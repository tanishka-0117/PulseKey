import qrcode
from PIL import Image
import json
import secrets
import os

class QRGenerator:
    def __init__(self, upload_folder='static/uploads'):
        self.upload_folder = upload_folder
        # Ensure upload directory exists
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder, exist_ok=True)
    
    def generate_medical_qr(self, report_data, user_id, report_id):
        """Generate QR code containing medical report access information"""
        try:
            # Create QR code data
            qr_data = {
                'report_id': report_id,
                'user_id': user_id,
                'type': 'medical_report',
                'access_url': f'/view_report/{report_id}'
            }
            
            # Convert to JSON string
            qr_json = json.dumps(qr_data)
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            
            qr.add_data(qr_json)
            qr.make(fit=True)
            
            # Create QR code image
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Generate filename and paths
            qr_filename = f"medical_qr_{report_id}.png"
            qr_filesystem_path = os.path.join(self.upload_folder, qr_filename)
            
            # Save QR code
            qr_img.save(qr_filesystem_path)
            
            # Verify file was created
            if os.path.exists(qr_filesystem_path) and os.path.getsize(qr_filesystem_path) > 0:
                # Return web-accessible path (relative to static folder)
                web_path = f"uploads/{qr_filename}"
                print(f"QR code generated successfully: {web_path}")
                return web_path, qr_filename
            else:
                print("QR code file creation failed")
                return None, None
                
        except Exception as e:
            print(f"QR generation error: {e}")
            return None, None
    
    def generate_share_qr(self, access_token, base_url):
        """Generate QR code for sharing access"""
        try:
            share_url = f"{base_url}/access_report/{access_token}"
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            
            qr.add_data(share_url)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="blue", back_color="white")
            
            qr_filename = f"share_qr_{secrets.token_hex(8)}.png"
            qr_filesystem_path = os.path.join(self.upload_folder, qr_filename)
            qr_img.save(qr_filesystem_path)
            
            # Return web-accessible path
            web_path = f"uploads/{qr_filename}"
            return web_path, share_url
            
        except Exception as e:
            print(f"Share QR generation error: {e}")
            return None, None