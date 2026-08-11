import pytesseract
from pytesseract import TesseractNotFoundError
from PIL import Image
import cv2
import numpy as np
import re
from datetime import datetime
import os


class OCRProcessor:

    def __init__(self):
        # Configure Tesseract path if available
        self.setup_tesseract_path()

    def setup_tesseract_path(self):
        """Configure Tesseract path for local Windows development."""

        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]

        username = os.getenv("USERNAME")
        if username:
            possible_paths.append(
                rf"C:\Users\{username}\AppData\Local\Tesseract-OCR\tesseract.exe"
            )

        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                print(f"Tesseract found at: {path}")
                return

        # Cloud deployments usually do not have Tesseract installed.
        try:
            pytesseract.get_tesseract_version()
            print("Tesseract found in PATH")
        except Exception:
            print("Tesseract OCR is not installed in this environment.")

    def is_tesseract_available(self):
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def preprocess_image(self, image_path):
        """Preprocess image for better OCR results."""

        try:
            img = cv2.imread(image_path)

            if img is None:
                raise ValueError("Could not read image")

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            denoised = cv2.medianBlur(gray, 5)

            _, thresh = cv2.threshold(
                denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            return thresh

        except Exception as e:
            print(f"Image preprocessing error: {e}")

            # PIL fallback
            try:
                img = Image.open(image_path)
                return np.array(img.convert("L"))
            except Exception as pil_error:
                print(f"PIL fallback error: {pil_error}")
                return None

    def extract_text(self, image_path):
        """Extract text from medical report image."""

        if not self.is_tesseract_available():
            return (
                "OCR service is unavailable because Tesseract is not installed "
                "on this server. Deploy on Render/Railway with Tesseract installed."
            )

        try:
            processed_image = self.preprocess_image(image_path)

            if processed_image is None:
                return None

            custom_config = (
                r"--oem 3 --psm 6 "
                r"-c tessedit_char_whitelist="
                r"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
                r"0123456789.,:;()-/ "
            )

            extracted_text = pytesseract.image_to_string(
                processed_image,
                config=custom_config
            )

            if not extracted_text.strip():
                extracted_text = pytesseract.image_to_string(processed_image)

            return extracted_text.strip()

        except TesseractNotFoundError:
            return (
                "Tesseract OCR is not installed on the server. "
                "Install Tesseract or deploy on Render."
            )

        except Exception as e:
            print(f"OCR Error: {e}")

            try:
                img = Image.open(image_path)
                return pytesseract.image_to_string(img)
            except Exception:
                return None

    def generate_summary(self, extracted_text):
        """Generate a summary of the medical report."""

        summary = {}

        if not extracted_text:
            return summary

        patterns = {
            "patient_name": (
                r"(?:patient|name|patient name)[:\s]*([A-Za-z\s]+[A-Za-z])"
            ),
            "age": r"(?:age|age:)[:\s]*(\d+)",
            "date": r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            "diagnosis": (
                r"(?:diagnosis|findings|impression)[:\s]*([^.\n]+)"
            ),
            "medications": (
                r"(?:medications|prescription|drugs)[:\s]*([^.\n]+)"
            ),
            "doctor": r"(?:doctor|physician|dr\.?)[:\s]*([A-Za-z\s.]+)",
            "hospital": (
                r"(?:hospital|clinic|medical center)[:\s]*([A-Za-z\s]+)"
            ),
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, extracted_text, re.IGNORECASE)
            if match:
                summary[key] = match.group(1).strip()

        words = extracted_text.split()
        lines = extracted_text.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]

        summary["word_count"] = len(words)
        summary["line_count"] = len(non_empty_lines)
        summary["extraction_date"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        if non_empty_lines:
            first_line = non_empty_lines[0]
            summary["preview"] = (
                first_line[:100] + "..."
                if len(first_line) > 100
                else first_line
            )

        return summary

    def process_medical_report(self, image_path):
        """Main method to process a medical report."""

        extracted_text = self.extract_text(image_path)

        if not extracted_text:
            return None, None

        summary = self.generate_summary(extracted_text)

        return extracted_text, summary
