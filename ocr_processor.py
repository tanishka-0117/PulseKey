import pytesseract
from PIL import Image
import cv2
import numpy as np
import re
from datetime import datetime
import os

class OCRProcessor:
    def __init__(self):
        # Set Tesseract path for Windows
        self.setup_tesseract_path()
    
    def setup_tesseract_path(self):
        """Configure Tesseract path for Windows"""
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME')),
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                print(f"Tesseract found at: {path}")
                return
        
        # If not found in common paths, try to use from PATH
        try:
            pytesseract.get_tesseract_version()
            print("Tesseract found in PATH")
        except:
            print("Warning: Tesseract not found. Please install Tesseract OCR")
    
    def preprocess_image(self, image_path):
        """Preprocess image for better OCR results"""
        try:
            # Read image
            img = cv2.imread(image_path)
            
            if img is None:
                raise ValueError("Could not read image")
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply noise removal
            denoised = cv2.medianBlur(gray, 5)
            
            # Apply thresholding
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return thresh
        
        except Exception as e:
            print(f"Image preprocessing error: {e}")
            # Try to load with PIL as fallback
            try:
                img = Image.open(image_path)
                return np.array(img.convert('L'))
            except Exception as pil_error:
                print(f"PIL fallback error: {pil_error}")
                return None
    
    def extract_text(self, image_path):
        """Extract text from medical report image"""
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image_path)
            
            if processed_image is None:
                return None
            
            # Perform OCR with different configurations for better results
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,:;()-/ '
            
            extracted_text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            # If no text found, try without whitelist
            if not extracted_text.strip():
                extracted_text = pytesseract.image_to_string(processed_image)
            
            return extracted_text.strip()
        
        except Exception as e:
            print(f"OCR Error: {e}")
            # Try simple PIL-based OCR as fallback
            try:
                img = Image.open(image_path)
                return pytesseract.image_to_string(img)
            except:
                return None
    
    def generate_summary(self, extracted_text):
        """Generate a summary of the medical report"""
        summary = {}
        
        if not extracted_text:
            return summary
        
        # Extract key information using patterns
        patterns = {
            'patient_name': r'(?:patient|name|patient name)[:\s]*([A-Za-z\s]+[A-Za-z])',
            'age': r'(?:age|age:)[:\s]*(\d+)',
            'date': r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            'diagnosis': r'(?:diagnosis|findings|impression)[:\s]*([^.\n]+)',
            'medications': r'(?:medications|prescription|drugs)[:\s]*([^.\n]+)',
            'doctor': r'(?:doctor|physician|dr\.?)[:\s]*([A-Za-z\s.]+)',
            'hospital': r'(?:hospital|clinic|medical center)[:\s]*([A-Za-z\s]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, extracted_text, re.IGNORECASE)
            if match:
                summary[key] = match.group(1).strip()
        
        # Count words and lines for basic metrics
        words = extracted_text.split()
        lines = extracted_text.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        summary['word_count'] = len(words)
        summary['line_count'] = len(non_empty_lines)
        summary['extraction_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Extract first few lines as preview
        if non_empty_lines:
            summary['preview'] = non_empty_lines[0][:100] + '...' if len(non_empty_lines[0]) > 100 else non_empty_lines[0]
        
        return summary
    
    def process_medical_report(self, image_path):
        """Main method to process medical report"""
        # Extract text
        extracted_text = self.extract_text(image_path)
        
        if not extracted_text:
            return None, None
        
        # Generate summary
        summary = self.generate_summary(extracted_text)
        
        return extracted_text, summary