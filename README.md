# PulseKey – Secure Medical Report Digitization & Sharing Platform

**PulseKey** is a secure, modular web application that digitizes paper-based medical records using **Optical Character Recognition (OCR)** and enables **time-limited QR-code-based sharing**. The platform is designed to reduce manual record handling, improve accessibility, and provide patients with strong control over their medical data.

---

## Problem Statement

Traditional medical records are often:

* Stored in paper form
* Difficult to search and organize
* Prone to loss or damage
* Insecure when shared manually
* Time-consuming for hospitals and patients to manage

PulseKey solves these issues by converting scanned reports into structured digital records and providing secure, temporary sharing links.

---

# Key Features

## OCR-Based Medical Report Digitization

* Image preprocessing using **OpenCV**
* Text extraction using **Tesseract OCR**
* Supports scanned prescriptions, lab reports, and medical documents

## Structured Data Extraction

* Converts unstructured OCR text into searchable summaries
* Extracts diagnoses, vitals, medications, and clinical observations using regular expressions

## Secure QR Code Sharing

* Generates a unique QR code for every report
* QR code points to a secure access URL

## Time-Limited Access Control

* Cryptographically secure URL-safe access tokens
* Configurable expiry period (up to **30 days**)
* Shared users receive **view-only access**

## Modular Architecture

Clear separation of concerns:

* **MedicalDatabase** → data management
* **OCRProcessor** → OCR pipeline
* **QRGenerator** → secure sharing

## Production-Ready Deployment

* Environment-variable configuration
* Gunicorn support
* Docker support
* Render/Railway deployment ready

---

# System Architecture

```text
User Upload
     |
     v
+------------------+
|  Flask Web App   |
+------------------+
     |
     +-------------------+
     |                   |
     v                   v
+-------------+     +-------------+
| OCRProcessor|     | QRGenerator |
+-------------+     +-------------+
     |
     v
+------------------+
| Structured Report|
+------------------+
     |
     v
+------------------+
| MedicalDatabase  |
+------------------+
     |
     v
Secure QR Link / Shared Access
```

---

# Tech Stack

| Layer             | Technology     |
| ----------------- | -------------- |
| Backend           | Flask (Python) |
| OCR Engine        | Tesseract OCR  |
| Image Processing  | OpenCV         |
| Database          | SQLite         |
| QR Generation     | qrcode         |
| Production Server | Gunicorn       |
| Containerization  | Docker         |

---

# Project Structure

```text
PulseKey/
├── app.py
├── database.py
├── ocr_processor.py
├── qr_generator.py
├── requirements.txt
├── templates/
├── static/
│   ├── uploads/
│   └── qrcodes/
├── Dockerfile
├── Procfile
└── README.md
```

---

# Installation

## 1. Clone the Repository

```bash
git clone https://github.com/tanishka-0117/PulseKey.git
cd PulseKey
```

## 2. Create a Virtual Environment

```bash
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Install Tesseract OCR

### Windows

Install from:
https://github.com/UB-Mannheim/tesseract/wiki

### Ubuntu / Debian

```bash
sudo apt-get install tesseract-ocr
```

## 5. Run the Application

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

# Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-long-random-secret
PORT=5000
```

---

# Docker Deployment

## Build Image

```bash
docker build -t pulsekey .
```

## Run Container

```bash
docker run -p 5000:5000 --env-file .env pulsekey
```

---

# Deploy on Render / Railway

## Build Command

```bash
pip install -r requirements.txt
```

## Start Command

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

Add the following environment variable in the deployment dashboard:

```env
SECRET_KEY=your-long-random-secret
```

---

# Security Features

* Secure random access tokens using `secrets.token_urlsafe`
* Time-bound sharing links
* View-only shared access
* Server-side session management
* Environment-based secret management
* Restricted file serving

---

# Future Enhancements

* PostgreSQL migration
* User authentication with JWT
* AES encryption for stored reports
* Role-based access control (Patient / Doctor / Admin)
* AI-based medical entity extraction
* PDF report support
* Cloud storage integration (AWS S3 / GCP)
