# Smart Document OCR & Validation

Aplikasi sederhana untuk OCR dokumen menggunakan **EasyOCR**, dilanjutkan dengan information extraction dan rule-based validation.

## Menjalankan Project

### 1. Clone repository

```bash
git clone https://github.com/PlainIceTea/Nalara--smart-document-ocr-4.git
cd Nalara--smart-document-ocr-4
```

### 2. Buat virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependency

```bash
python -m pip install -r requirements.txt
```

### 4. Jalankan aplikasi

```bash
python -m streamlit run app.py
```

Aplikasi akan terbuka di:

```text
http://localhost:8501
```

## Fitur

* Upload dokumen JPG/PNG
* OCR menggunakan EasyOCR
* Bounding box dan confidence
* Information extraction
* Validation status:

  * `VALID`
  * `INCOMPLETE`
  * `NEEDS REVIEW`

## Jenis Dokumen

* DOCUMENT
* FORM
* INVOICE
* REAL_LIFE
