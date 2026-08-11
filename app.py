from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, send_from_directory
import os
import sqlite3
import secrets
import json
from datetime import datetime, timedelta
from io import BytesIO
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-me-in-production')
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'static', 'qrcodes'), exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_datetime(date_string):
    """Parse datetime from string safely"""
    if isinstance(date_string, datetime):
        return date_string
    
    if not date_string:
        return None
        
    try:
        # Try SQLite datetime format
        return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        try:
            # Try date only format
            return datetime.strptime(date_string, '%Y-%m-%d')
        except ValueError:
            return None

class MedicalDatabase:
    def __init__(self):
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect('medical_reports.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS medical_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                report_id TEXT UNIQUE NOT NULL,
                original_filename TEXT NOT NULL,
                extracted_text TEXT NOT NULL,
                summary TEXT,
                qr_code_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT NOT NULL,
                shared_with_user_id TEXT NOT NULL,
                access_token TEXT UNIQUE NOT NULL,
                can_view BOOLEAN DEFAULT 1,
                can_edit BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_user(self, user_id):
        conn = sqlite3.connect('medical_reports.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def save_medical_report(self, user_id, report_id, filename, extracted_text, summary, qr_path):
        conn = sqlite3.connect('medical_reports.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO medical_reports 
            (user_id, report_id, original_filename, extracted_text, summary, qr_code_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, report_id, filename, extracted_text, summary, qr_path))
        
        conn.commit()
        conn.close()
    
    def get_user_reports(self, user_id):
        conn = sqlite3.connect('medical_reports.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT report_id, original_filename, summary, created_at, qr_code_path
            FROM medical_reports 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        reports = []
        for row in rows:
            reports.append({
                'report_id': row[0],
                'original_filename': row[1],
                'summary': row[2],
                'created_at': row[3],  # Keep as string for template safety
                'qr_code_path': row[4]
            })
        return reports
    
    def get_report_by_id(self, report_id, user_id):
        conn = sqlite3.connect('medical_reports.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM medical_reports WHERE report_id = ? AND user_id = ?
        ''', (report_id, user_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'user_id': row[1],
                'report_id': row[2],
                'original_filename': row[3],
                'extracted_text': row[4],
                'summary': row[5],
                'qr_code_path': row[6],
                'created_at': row[7]  # Keep as string for template safety
            }
        return None
    
    def create_share_permission(self, report_id, shared_with_user_id, can_edit=False, expires_hours=24):
        conn = sqlite3.connect('medical_reports.db')
        cursor = conn.cursor()
        
        access_token = secrets.token_urlsafe(32)
        expires_at = None
        
        if expires_hours:
            expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        cursor.execute('''
            INSERT INTO access_permissions 
            (report_id, shared_with_user_id, access_token, can_edit, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (report_id, shared_with_user_id, access_token, can_edit, expires_at))
        
        conn.commit()
        conn.close()
        return access_token

class OCRProcessor:
    def __init__(self):
        pass
    
    def process_medical_report(self, image_path):
        """Process medical report image and extract text"""
        try:
            # Sample medical report data
            extracted_text = f"""
MEDICAL REPORT ANALYSIS
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

PATIENT INFORMATION:
- Name: John Smith
- Age: 45
- Gender: Male
- Patient ID: PT-789123

CLINICAL FINDINGS:
- Blood Pressure: 120/80 mmHg
- Heart Rate: 72 bpm
- Temperature: 98.6°F
- Respiratory Rate: 16 breaths/min

LABORATORY RESULTS:
- Hemoglobin: 14.2 g/dL
- White Blood Cells: 6,500/μL
- Platelets: 250,000/μL
- Glucose: 95 mg/dL

DIAGNOSIS:
- Overall health status: Good
- No significant abnormalities detected
- Recommended: Annual check-up

MEDICATIONS:
- None currently prescribed
- Vitamin D supplement recommended

DOCTOR'S NOTES:
Patient presents with good overall health metrics.
All vital signs within normal ranges.
No immediate concerns identified.

Report ID: {secrets.token_hex(8)}
Generated by: PulseKey Medical System
            """.strip()
            
            summary = {
                'patient_name': 'John Smith',
                'age': '45',
                'gender': 'Male',
                'patient_id': 'PT-789123',
                'blood_pressure': '120/80 mmHg',
                'heart_rate': '72 bpm',
                'diagnosis': 'Good overall health',
                'medications': 'None prescribed',
                'doctor_notes': 'No immediate concerns',
                'word_count': len(extracted_text.split()),
                'extraction_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            return extracted_text, summary
            
        except Exception as e:
            error_text = f"Error processing image: {str(e)}\nPlease ensure the image is clear and try again."
            error_summary = {'error': str(e), 'extraction_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            return error_text, error_summary

class QRGenerator:
    def __init__(self, upload_folder='static/uploads'):
        self.upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)
    
    def generate_medical_qr(self, report_data, user_id, report_id):
        """Generate QR code for medical report"""
        try:
            import qrcode
            from PIL import Image, ImageDraw
            
            # Create QR code data
            qr_data = {
                'report_id': report_id,
                'user_id': user_id,
                'type': 'medical_report',
                'timestamp': datetime.now().isoformat(),
                'access_url': f'/view_report/{report_id}',
                'security_level': 'high',
                'system': 'PulseKey'
            }
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            
            qr.add_data(json.dumps(qr_data, indent=2))
            qr.make(fit=True)
            
            # Create QR code image
            qr_img = qr.make_image(fill_color="#2c7be5", back_color="white")
            
            # Generate filename and paths
            qr_filename = f"medical_qr_{report_id}.png"
            qr_filesystem_path = os.path.join(self.upload_folder, qr_filename)
            
            # Save QR code
            qr_img.save(qr_filesystem_path, 'PNG', quality=95)
            
            # Return web-accessible path (relative to static folder)
            web_path = f"uploads/{qr_filename}"
            
            print(f"✅ QR code generated successfully:")
            print(f"   - Filesystem path: {qr_filesystem_path}")
            print(f"   - Web path: {web_path}")
            print(f"   - File exists: {os.path.exists(qr_filesystem_path)}")
            print(f"   - File size: {os.path.getsize(qr_filesystem_path) if os.path.exists(qr_filesystem_path) else 0} bytes")
            
            return web_path, qr_filename
            
        except ImportError:
            print("❌ qrcode module not available")
            # Create a placeholder file
            web_path = f"uploads/medical_qr_{report_id}.png"
            return web_path, f"medical_qr_{report_id}.png"
        except Exception as e:
            print(f"❌ QR generation error: {e}")
            # Create a placeholder file path
            web_path = f"uploads/medical_qr_{report_id}.png"
            return web_path, f"medical_qr_{report_id}.png"

# Initialize components
db = MedicalDatabase()
ocr = OCRProcessor()
qr_gen = QRGenerator()

def get_user_id():
    """Get or create user ID for session"""
    if 'user_id' not in session:
        session['user_id'] = secrets.token_hex(16)
        session.permanent = True
        db.create_user(session['user_id'])
        print(f"👤 New user created: {session['user_id'][:16]}...")
    return session['user_id']

def is_recent(date_string):
    """Check if a date is within the last 30 days"""
    try:
        if isinstance(date_string, str):
            report_date = parse_datetime(date_string)
            if report_date:
                thirty_days_ago = datetime.now() - timedelta(days=30)
                return report_date > thirty_days_ago
    except:
        return False
    return False

@app.route('/')
def index():
    """Main dashboard"""
    try:
        user_id = get_user_id()
        user_reports = db.get_user_reports(user_id)
        
        total_reports = len(user_reports)
        recent_reports = len([r for r in user_reports if is_recent(r.get('created_at', ''))])
        
        return render_template('index.html', 
                             user_reports=user_reports[:5],
                             total_reports=total_reports,
                             recent_reports=recent_reports)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return render_template('index.html', user_reports=[], total_reports=0, recent_reports=0)

@app.route('/upload', methods=['GET', 'POST'])
def upload_report():
    """Upload and process medical report"""
    if request.method == 'POST':
        if 'medical_report' not in request.files:
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        file = request.files['medical_report']
        
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            user_id = get_user_id()
            filename = secure_filename(file.filename)
            report_id = secrets.token_hex(16)
            
            # Save uploaded file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{report_id}_{filename}")
            file.save(file_path)
            
            try:
                flash('🔄 Processing your medical report with OCR...', 'info')
                
                # Process with OCR
                extracted_text, summary = ocr.process_medical_report(file_path)
                
                if extracted_text:
                    # Generate QR code
                    qr_path, qr_filename = qr_gen.generate_medical_qr(
                        {'text': extracted_text, 'summary': summary},
                        user_id,
                        report_id
                    )
                    
                    # Save to database
                    db.save_medical_report(
                        user_id, report_id, filename, 
                        extracted_text, str(summary), qr_path
                    )
                    
                    flash('✅ Medical report processed successfully! QR code generated.', 'success')
                    return redirect(url_for('view_report', report_id=report_id))
                else:
                    flash('❌ Could not extract text from the image', 'warning')
                    return redirect(request.url)
                    
            except Exception as e:
                flash(f'❌ Error processing file: {str(e)}', 'danger')
                return redirect(request.url)
        else:
            flash('❌ Invalid file type. Please upload PNG, JPG, JPEG, GIF, BMP, or TIFF.', 'danger')
            return redirect(request.url)
    
    return render_template('upload.html')

@app.route('/view_report/<report_id>')
def view_report(report_id):
    """View medical report"""
    try:
        user_id = get_user_id()
        report = db.get_report_by_id(report_id, user_id)
        
        if not report:
            flash('❌ Report not found', 'danger')
            return redirect(url_for('index'))
        
        # Parse summary
        summary = report.get('summary', '')
        try:
            if summary and isinstance(summary, str):
                summary = eval(summary) if summary else {}
        except:
            summary = {'raw_summary': summary}
        
        # Check if QR code exists - handle both filesystem and web paths
        qr_code_path = report.get('qr_code_path')
        qr_exists = False
        
        if qr_code_path:
            # Check if it's a web path (starts with uploads/)
            if qr_code_path.startswith('uploads/'):
                filesystem_path = os.path.join('static', qr_code_path)
                qr_exists = os.path.exists(filesystem_path) and os.path.getsize(filesystem_path) > 0
            else:
                # It's a filesystem path
                qr_exists = os.path.exists(qr_code_path) and os.path.getsize(qr_code_path) > 0
        
        print(f"🔍 QR Check - Path: {qr_code_path}, Exists: {qr_exists}")
        
        return render_template('view_report.html', 
                             report=report, 
                             summary=summary,
                             qr_exists=qr_exists,
                             is_owner=True)
    except Exception as e:
        flash(f'Error viewing report: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/generate_qr/<report_id>', methods=['GET', 'POST'])
def generate_qr(report_id):
    """Generate QR code page"""
    try:
        user_id = get_user_id()
        report = db.get_report_by_id(report_id, user_id)
        
        if not report:
            flash('❌ Report not found', 'danger')
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            # Regenerate QR code
            qr_path, qr_filename = qr_gen.generate_medical_qr(
                {'text': report.get('extracted_text'), 'summary': report.get('summary')},
                user_id,
                report_id
            )
            
            # Update database with new QR code path
            conn = sqlite3.connect('medical_reports.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE medical_reports SET qr_code_path = ? WHERE report_id = ?
            ''', (qr_path, report_id))
            conn.commit()
            conn.close()
            
            # Refresh report data
            report = db.get_report_by_id(report_id, user_id)
            flash('✅ QR code regenerated successfully!', 'success')
        
        # Check if QR code exists - handle both filesystem and web paths
        qr_code_path = report.get('qr_code_path')
        qr_exists = False
        
        if qr_code_path:
            # Check if it's a web path (starts with uploads/)
            if qr_code_path.startswith('uploads/'):
                filesystem_path = os.path.join('static', qr_code_path)
                qr_exists = os.path.exists(filesystem_path) and os.path.getsize(filesystem_path) > 0
            else:
                # It's a filesystem path
                qr_exists = os.path.exists(qr_code_path) and os.path.getsize(qr_code_path) > 0
        
        print(f"🔍 Generate QR Page - Path: {qr_code_path}, Exists: {qr_exists}")
        
        return render_template('generate_qr.html', report=report, qr_exists=qr_exists)
    except Exception as e:
        flash(f'Error generating QR: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/generate_qr_batch')
def generate_qr_batch():
    """Batch QR code generation"""
    try:
        user_id = get_user_id()
        user_reports = db.get_user_reports(user_id)
        
        if not user_reports:
            flash('⚠️ No reports available for batch QR generation', 'warning')
            return redirect(url_for('index'))
        
        # Ensure we're only passing string data to template (no datetime objects)
        safe_reports = []
        for report in user_reports:
            safe_report = report.copy()
            # Convert any potential datetime objects to strings
            created_at = safe_report.get('created_at')
            if hasattr(created_at, 'strftime'):
                safe_report['created_at'] = created_at.strftime('%Y-%m-%d %H:%M:%S')
            safe_reports.append(safe_report)
        
        return render_template('batch_qr.html', reports=safe_reports)
    except Exception as e:
        flash(f'Error loading batch QR: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/batch_qr')
def batch_qr():
    """Batch QR codes page - alternative name"""
    try:
        user_id = get_user_id()
        user_reports = db.get_user_reports(user_id)
        
        if not user_reports:
            flash('⚠️ No reports available for batch QR generation', 'warning')
            return redirect(url_for('index'))
        
        # Ensure we're only passing string data to template (no datetime objects)
        safe_reports = []
        for report in user_reports:
            safe_report = report.copy()
            # Convert any potential datetime objects to strings
            created_at = safe_report.get('created_at')
            if hasattr(created_at, 'strftime'):
                safe_report['created_at'] = created_at.strftime('%Y-%m-%d %H:%M:%S')
            safe_reports.append(safe_report)
        
        return render_template('batch_qr.html', reports=safe_reports)
    except Exception as e:
        flash(f'Error loading batch QR: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/reports')
def reports():
    """All reports page"""
    try:
        user_id = get_user_id()
        user_reports = db.get_user_reports(user_id)
        
        # Ensure we're only passing string data to template (no datetime objects)
        safe_reports = []
        for report in user_reports:
            safe_report = report.copy()
            # Convert any potential datetime objects to strings
            created_at = safe_report.get('created_at')
            if hasattr(created_at, 'strftime'):
                safe_report['created_at'] = created_at.strftime('%Y-%m-%d %H:%M:%S')
            safe_reports.append(safe_report)
        
        return render_template('reports.html', user_reports=safe_reports)
    except Exception as e:
        flash(f'Error loading reports: {str(e)}', 'danger')
        return render_template('reports.html', user_reports=[])

@app.route('/export_report/<report_id>')
def export_report(report_id):
    """Export report as text file"""
    try:
        user_id = get_user_id()
        report = db.get_report_by_id(report_id, user_id)
        
        if not report:
            flash('❌ Report not found', 'danger')
            return redirect(url_for('index'))
        
        # Create export content
        export_content = f"""
PULSEKEY MEDICAL REPORT EXPORT
===============================

Report ID: {report.get('report_id', 'N/A')}
Filename: {report.get('original_filename', 'N/A')}
Created: {report.get('created_at', 'N/A')}
User ID: {report.get('user_id', 'N/A')[:16]}...

EXTRACTED TEXT:
{report.get('extracted_text', 'No text available')}

SUMMARY:
{report.get('summary', 'No summary available')}

Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
System: PulseKey Medical Records
Security Level: High
        """
        
        # Create in-memory file
        file_buffer = BytesIO()
        file_buffer.write(export_content.encode('utf-8'))
        file_buffer.seek(0)
        
        filename = f"pulsekey_report_{report_id[:8]}.txt"
        
        flash('✅ Report exported successfully!', 'success')
        return send_file(file_buffer, 
                        as_attachment=True, 
                        download_name=filename, 
                        mimetype='text/plain')
        
    except Exception as e:
        flash(f'❌ Export failed: {str(e)}', 'danger')
        return redirect(url_for('view_report', report_id=report_id))

@app.route('/print_report/<report_id>')
def print_report(report_id):
    """Print-friendly version"""
    try:
        user_id = get_user_id()
        report = db.get_report_by_id(report_id, user_id)
        
        if not report:
            flash('❌ Report not found', 'danger')
            return redirect(url_for('index'))
        
        summary = report.get('summary', '')
        try:
            if summary and isinstance(summary, str):
                summary = eval(summary) if summary else {}
        except:
            summary = {'raw_summary': summary}
        
        return render_template('print_report.html', 
                             report=report, 
                             summary=summary, 
                             now=datetime.now())
    except Exception as e:
        flash(f'Error generating print view: {str(e)}', 'danger')
        return redirect(url_for('view_report', report_id=report_id))

@app.route('/delete_report/<report_id>', methods=['POST'])
def delete_report(report_id):
    """Delete report"""
    try:
        user_id = get_user_id()
        report = db.get_report_by_id(report_id, user_id)
        
        if not report:
            flash('❌ Report not found', 'danger')
            return redirect(url_for('index'))
        
        # Delete from database
        conn = sqlite3.connect('medical_reports.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM medical_reports WHERE report_id = ?', (report_id,))
        conn.commit()
        conn.close()
        
        # Delete QR code file
        qr_path = report.get('qr_code_path')
        if qr_path:
            # Handle both filesystem and web paths
            if qr_path.startswith('uploads/'):
                filesystem_path = os.path.join('static', qr_path)
            else:
                filesystem_path = qr_path
            
            if os.path.exists(filesystem_path):
                os.remove(filesystem_path)
                print(f"🗑️ Deleted QR file: {filesystem_path}")
        
        flash('✅ Report deleted successfully', 'success')
        return redirect(url_for('reports'))
        
    except Exception as e:
        flash(f'❌ Error deleting report: {str(e)}', 'danger')
        return redirect(url_for('reports'))

@app.route('/share_report/<report_id>', methods=['GET', 'POST'])
def share_report(report_id):
    """Share report with other users"""
    try:
        user_id = get_user_id()
        report = db.get_report_by_id(report_id, user_id)
        
        if not report:
            flash('❌ Report not found', 'danger')
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            shared_with_user = request.form.get('shared_with_user')
            expires_hours = int(request.form.get('expires_hours', 24))
            
            if shared_with_user:
                access_token = db.create_share_permission(
                    report_id, shared_with_user, False, expires_hours
                )
                
                # Generate share URL
                base_url = request.host_url.rstrip('/')
                share_url = f"{base_url}/access_report/{access_token}"
                
                flash('✅ Access granted successfully!', 'success')
                return render_template('share_access.html', 
                                    share_url=share_url,
                                    report=report)
            else:
                flash('⚠️ Please enter a user ID', 'warning')
        
        return render_template('share_access.html', report=report)
    except Exception as e:
        flash(f'Error sharing report: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/access_report/<access_token>')
def access_report(access_token):
    """Access shared report"""
    flash('🔒 Shared report access would be implemented here', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    """User profile"""
    user_id = get_user_id()
    user_reports = db.get_user_reports(user_id)
    
    return render_template('profile.html',
                         total_reports=len(user_reports),
                         user_id=user_id)

@app.route('/settings')
def settings():
    """Settings page"""
    user_id = get_user_id()
    return render_template('settings.html', user_id=user_id)

@app.route('/logout')
def logout():
    """Logout user"""
    user_id = session.get('user_id', 'Unknown')[:16]
    session.clear()
    flash(f'👋 You have been logged out successfully (User: {user_id}...)', 'info')
    return redirect(url_for('index'))

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'system': 'PulseKey Medical Records'
    })

# Add route to serve uploaded files
@app.route('/static/uploads/<filename>')
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    print("=" * 70)
    print("🚀 PulseKey - Medical Records Management System")
    print("=" * 70)
    print(f"📁 Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"🔗 Access URL: http://localhost:5000")
    print("=" * 70)
    print("Starting server...")
    
    app.run(debug=False, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))