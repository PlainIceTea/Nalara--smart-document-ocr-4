import re


# =========================================================
# GENERAL
# =========================================================

def normalize_text(text):
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def extract_between(text, start_pattern, end_pattern):
    match = re.search(
        rf"{start_pattern}\s*(.*?)\s*(?={end_pattern})",
        text,
        re.IGNORECASE
    )

    return match.group(1).strip(" :-") if match else None


# =========================================================
# DOCUMENT
# =========================================================

def find_document_id(raw_text, ocr_results, image_height=None):
    patterns = [
        r"\b[A-Z]{1,3}\d{1,3}-\d{2,5}\b",
        r"\b[A-Z]{1,3}-\d{2,5}\b"
    ]

    # Prioritas: cari kode di bagian atas dokumen
    if image_height:
        header_limit = image_height * 0.30

        for item in ocr_results:
            box = item["box"]
            center_y = sum(p[1] for p in box) / len(box)

            if center_y <= header_limit:
                for pattern in patterns:
                    match = re.search(
                        pattern,
                        item["text"],
                        re.IGNORECASE
                    )

                    if match:
                        return match.group(0).upper()

    # Fallback: cari di seluruh raw text
    for pattern in patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)

        if match:
            return match.group(0).upper()

    return None


def find_name(ocr_results):
    for i, item in enumerate(ocr_results):
        text = item["text"].strip()

        # Name: John Doe
        match = re.search(
            r"(?i)\b(?:name|nama)\b\s*[:\-]\s*(.+)",
            text
        )

        if match and match.group(1).strip():
            return match.group(1).strip()

        # Name: terpisah dari value
        if text.lower() in {"name", "name:", "nama", "nama:"}:
            if i + 1 < len(ocr_results):
                return ocr_results[i + 1]["text"].strip()

    return None


# =========================================================
# FORM
# =========================================================

def find_form_from(text):
    return extract_between(
        text,
        r"\bFROM\s*:",
        r"\bTO\s*:"
    )


def find_form_to(text):
    return extract_between(
        text,
        r"\bTO\s*:",
        r"\bCC\s*:"
    )


MONTHS = (
    r"January|February|March|April|May|June|"
    r"July|August|September|October|November|December"
)


def clean_date(value):
    if not value:
        return None

    value = re.sub(r"\s+", " ", value).strip()

    # December 31 . 1992
    match = re.search(
        rf"\b({MONTHS})\s+(\d{{1,2}})\s*[,.\-]?\s*(\d{{4}})\b",
        value,
        re.IGNORECASE
    )

    if match:
        month, day, year = match.groups()
        return f"{month} {day}, {year}"

    # September 1992
    match = re.search(
        rf"\b({MONTHS})\s+(\d{{4}})\b",
        value,
        re.IGNORECASE
    )

    if match:
        month, year = match.groups()
        return f"{month} {year}"

    return value


def find_issue_date(text):
    value = extract_between(
        text,
        r"\bCOUPON\s+ISSUE\s+DATE\b",
        r"\bCOUPON\s+EXPIRATION\s+DATE\b"
    )

    return clean_date(value)


def find_expiration_date(text):
    value = extract_between(
        text,
        r"\bCOUPON\s+EXPIRATION\s+DATE\b",
        r"\bCIRCULATION\b"
    )

    return clean_date(value)


# =========================================================
# INVOICE
# =========================================================

def find_invoice_number(text):
    patterns = [
        # Kita kembalikan logika lookahead (?=[\s:\-]|$) yang sangat brilian ini!
        r"(?i)\b(?:tax\s*invoice|cash\s+inv|invoice|involce|inv)\b"
        r"\s*(?:#|(?:no\.?|number|[a-z]+)(?=[\s:\-]|$))?"
        r"\s*[:\-]?\s*"
        r"([A-Z0-9./_-]{3,})",

        r"(?i)(?:no\.?\s*invoice|no\.?\s*involce)\s*[:\-]?\s*([A-Z0-9./_-]{3,})",
        r"(?i)\breceipt\s*[:\-]?\s*([A-Z0-9./_-]{3,})",
        r"\b([A-Z]{2,5}-\d{2,}-\d{4,})\b"
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            candidate = match.group(1).strip()
            if any(char.isdigit() for char in candidate):
                return candidate

    return None

def find_invoice_date(text):
    patterns = [
        # Format dengan label (Date:, Tgl:, DD:)
        r"(?i)\b(?:date|tgl|dd)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        # Format teks nama bulan (07 May 2018 / 06 Jun 2018)
        r"(?i)\b(\d{1,2}\s+(?:Jan(?:uari)?|Feb(?:ruari)?|Mar(?:et)?|Apr(?:il)?|May|Mei|Jun(?:i)?|Jul(?:i)?|Aug|Agu(?:stus)?|Sep(?:tember)?|Oct|Okt(?:ober)?|Nov(?:ember)?|Dec|Des(?:ember)?)\s+\d{2,4})\b",
        # Tanggal mandiri tanpa label (20/06/18 atau 25/03/2018)
        r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return match.group(1)

    return None


def find_total_amount(text):
    excluded = [
        "total qty",
        "total points",
        "total saving",
        "total gst",
        "sub total",
        "sub-total",
        "subtotal"
    ]

    pattern = (
        r"(?i)\b(?:grand\s+total|nett\s+total|net\s+total|total\s+amount|total\s+gross|total|jumlah)\b"
        r"(?:\s+(?:sales|incl|excl|supply|supplies|due))*"
        r"(?:\s*(?:\(?(?:RM|USD|IDR|RP|\$)\)?))?"
        r"\s*[:\-]?\s*"
        r"[$RM\s]*([0-9]{1,3}(?:\.[0-9]{3})+(?:,[0-9]{2})?|[0-9]+[.,][0-9]{2})"
    )

    candidates = []

    for match in re.finditer(pattern, text):
        start = max(0, match.start() - 25)
        context = text[start:match.end()].lower()

        if any(word in context for word in excluded):
            continue

        candidates.append(match.group(1))

    return candidates[-1] if candidates else None

def find_total_from_ocr(ocr_results):
    excluded = [
        "sub total",
        "sub-total",
        "subtotal",
        "total qty",
        "total points",
        "total saving",
        "total gst"
    ]

    for i, item in enumerate(ocr_results):
        text = item["text"].strip().lower()

        if any(word in text for word in excluded):
            continue

        if any(k in text for k in ["total", "grand", "nett", "net total", "amount"]):
            # Cek di box yang sama
            match = re.search(r"([0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+[.,][0-9]{2})", item["text"])
            if match:
                return match.group(1)

            # Cek hingga 10 box ke depan
            for j in range(1, 10):
                if i + j < len(ocr_results):
                    next_text = ocr_results[i + j]["text"]
                    match = re.search(r"([0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+[.,][0-9]{2})", next_text)
                    if match:
                        return match.group(1)

    return None

def find_invoice_number_from_ocr(ocr_results):
    keyword_pattern = re.compile(r"(?i)nvoice")

    for i, item in enumerate(ocr_results):
        text = item["text"].strip()

        if not keyword_pattern.search(text):
            continue

        match = re.search(r"([A-Z0-9./_-]{5,})\s*$", text, re.IGNORECASE)
        if match and any(c.isdigit() for c in match.group(1)):
            return match.group(1)

        if i + 1 < len(ocr_results):
            candidate = ocr_results[i + 1]["text"].strip()
            if any(c.isdigit() for c in candidate) and len(candidate) >= 3:
                return candidate

    return None

def find_invoice_number_from_ocr(ocr_results):
    """
    Fallback berbasis box OCR (bukan raw_text gabungan).
    Pakai substring 'nvoice' (bukan 'invoice' penuh) karena huruf
    pertama sering salah baca jadi 'lnvoice' / '1nvoice' saat
    confidence box rendah — jadi tetap ke-detect walau typo.
    """
    keyword_pattern = re.compile(r"(?i)nvoice")

    for i, item in enumerate(ocr_results):
        text = item["text"].strip()

        if not keyword_pattern.search(text):
            continue

        # kasus 1: angka nempel di box yang sama, misal "Invoice number: 01000339450"
        match = re.search(r"([A-Z0-9./_-]{5,})\s*$", text, re.IGNORECASE)
        if match and any(c.isdigit() for c in match.group(1)):
            return match.group(1)

        # kasus 2: label & angka kepisah jadi 2 box, angka ada di box berikutnya
        if i + 1 < len(ocr_results):
            candidate = ocr_results[i + 1]["text"].strip()
            if any(c.isdigit() for c in candidate) and len(candidate) >= 3:
                return candidate

    return None


    
# =========================================================
# MAIN EXTRACTION
# =========================================================

def extract_fields(
    document_type,
    raw_text,
    ocr_results,
    image_height=None
):
    text = normalize_text(raw_text)

    if document_type == "DOCUMENT":
        return {
            "document_id": find_document_id(
                raw_text,
                ocr_results,
                image_height
            ),
            "name": find_name(ocr_results),
            "raw_text": raw_text or None
        }

    if document_type == "FORM":
        return {
            "from": find_form_from(text),
            "to": find_form_to(text),
            "issue_date": find_issue_date(text),
            "expiration_date": find_expiration_date(text),
            "raw_text": raw_text or None
        }

    if document_type == "INVOICE":
        total = find_total_amount(text)
    if not total:
        total = find_total_from_ocr(ocr_results)

    invoice_number = find_invoice_number(text)
    if not invoice_number:                                   # <-- tambahan
        invoice_number = find_invoice_number_from_ocr(ocr_results)

    return {
        "invoice_number": invoice_number,
        "date": find_invoice_date(text),
        "total_amount": total,
        "raw_text": raw_text or None
    }

    if document_type == "REAL_LIFE":
        return {
            "raw_text": raw_text or None
        }

    return {}
