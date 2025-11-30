# PulseKey
PulseKey is a secure, modular web system that uses OCR and QR codes to automate the digitization, structuring, and time-limited sharing of paper-based medical records.

PulseKey is a robust, modular web application designed to securely digitize, structure, and manage personal medical reports. The system addresses the inefficiencies and security risks associated with traditional paper-based documentation by leveraging advanced Optical Character Recognition (OCR) and QR Code technology. Built on the lightweight Flask framework, PulseKey provides users with an intuitive interface to centralize their health records and maintain strict control over data access.

Core Features
Automated Data Digitization: Utilizes the OCRProcessor module, employing opencv-python for image preprocessing (grayscale, median blur, Otsu's thresholding) and pytesseract for accurate text extraction from image-based medical reports.

Structured Summary Generation: Converts unstructured raw OCR output into a clean, searchable structured summary using Regular Expressions, extracting key clinical data points like diagnoses and vitals.

Secure QR Code Access: Generates unique QR codes for every report. These codes encode a secure link to the record, streamlining retrieval and verification.

Granular Access Control: Implements a rigorous token-based sharing protocol where access is granted via a unique, 32-byte URL-safe access token and is strictly time-limited (configurable up to 30 days). Shared access is restricted to view-only.

Modular Architecture: Uses a three-tier Flask architecture with separate modules for data management (MedicalDatabase), processing (OCRProcessor), and sharing (QRGenerator), ensuring scalability and clear separation of concerns.

