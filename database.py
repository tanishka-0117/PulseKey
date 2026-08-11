import sqlite3
import json
from datetime import datetime
import secrets
import os

class MedicalDatabase:
    def __init__(self, db_name='medical_reports.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        """Get database connection with proper error handling"""
        try:
            conn = sqlite3.connect(self.db_name)
            conn.row_factory = sqlite3.Row  # This enables column access by name
            return conn
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            raise
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Medical reports table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS medical_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                report_id TEXT UNIQUE NOT NULL,
                original_filename TEXT NOT NULL,
                extracted_text TEXT NOT NULL,
                summary TEXT,
                qr_code_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Access permissions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT NOT NULL,
                shared_with_user_id TEXT NOT NULL,
                access_token TEXT UNIQUE NOT NULL,
                can_view BOOLEAN DEFAULT 1,
                can_edit BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (report_id) REFERENCES medical_reports (report_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_user(self, user_id):
        conn = self.get_connection()
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
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO medical_reports 
            (user_id, report_id, original_filename, extracted_text, summary, qr_code_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, report_id, filename, extracted_text, summary, qr_path))
        
        conn.commit()
        conn.close()
    
    def get_user_reports(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT report_id, original_filename, summary, created_at, qr_code_path
            FROM medical_reports 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert rows to list of dictionaries
        reports = []
        for row in rows:
            reports.append({
                'report_id': row[0],
                'original_filename': row[1],
                'summary': row[2],
                'created_at': row[3],
                'qr_code_path': row[4]
            })
        return reports
    
    def get_report_by_id(self, report_id, requesting_user_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if user owns the report or has permission
        cursor.execute('''
            SELECT mr.*, u.user_id as owner_id
            FROM medical_reports mr
            JOIN users u ON mr.user_id = u.user_id
            WHERE mr.report_id = ?
        ''', (report_id,))
        
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        # Convert row to dictionary
        report_dict = {
            'id': row[0],
            'user_id': row[1],
            'report_id': row[2],
            'original_filename': row[3],
            'extracted_text': row[4],
            'summary': row[5],
            'qr_code_path': row[6],
            'created_at': row[7],
            'owner_id': row[8] if len(row) > 8 else row[1]
        }
        
        # If requesting user is not the owner, check permissions
        if requesting_user_id and requesting_user_id != report_dict['user_id']:
            cursor.execute('''
                SELECT can_view, can_edit 
                FROM access_permissions 
                WHERE report_id = ? AND shared_with_user_id = ? 
                AND (expires_at IS NULL OR expires_at > datetime('now'))
            ''', (report_id, requesting_user_id))
            
            permission = cursor.fetchone()
            if not permission or not permission[0]:  # can_view check
                conn.close()
                return None
        
        conn.close()
        return report_dict
    
    def create_share_permission(self, report_id, shared_with_user_id, can_edit=False, expires_hours=24):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        access_token = secrets.token_urlsafe(32)
        expires_at = None
        
        if expires_hours:
            expires_at = datetime.now().timestamp() + (expires_hours * 3600)
            expires_at = datetime.fromtimestamp(expires_at)
        
        cursor.execute('''
            INSERT INTO access_permissions 
            (report_id, shared_with_user_id, access_token, can_edit, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (report_id, shared_with_user_id, access_token, can_edit, expires_at))
        
        conn.commit()
        conn.close()
        return access_token
    
    def get_shared_reports(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT mr.report_id, mr.original_filename, mr.summary, 
                   mr.created_at, ap.can_edit, u.user_id as owner_id
            FROM medical_reports mr
            JOIN access_permissions ap ON mr.report_id = ap.report_id
            JOIN users u ON mr.user_id = u.user_id
            WHERE ap.shared_with_user_id = ? 
            AND (ap.expires_at IS NULL OR ap.expires_at > datetime('now'))
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        shared_reports = []
        for row in rows:
            shared_reports.append({
                'report_id': row[0],
                'original_filename': row[1],
                'summary': row[2],
                'created_at': row[3],
                'can_edit': row[4],
                'owner_id': row[5]
            })
        return shared_reports
    
    def delete_report(self, report_id):
        """Delete a report and its associated permissions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Delete permissions first
            cursor.execute('DELETE FROM access_permissions WHERE report_id = ?', (report_id,))
            # Delete report
            cursor.execute('DELETE FROM medical_reports WHERE report_id = ?', (report_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting report: {e}")
            return False
        finally:
            conn.close()