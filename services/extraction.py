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
        # Tax Invoice : DSP05201803250022
        r"(?i)\btax\s+invoice\s*[:\-]?\s*([A-Z0-9][A-Z0-9./_-]{3,})",

        # Invoice No : INV001
        r"(?i)\binvoice\s*(?:number|no\.?|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9./_-]{3,})",

        # Receipt : CS00084670
        r"(?i)\breceipt\s*[:\-]?\s*([A-Z0-9][A-Z0-9./_-]{3,})"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return match.group(1).strip()

    return None


def find_invoice_date(text):
    patterns = [
        r"(?i)\bdate\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
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
        r"(?i)\btotal\s*"
        r"(?:\(?(?:RM|USD|IDR)\)?)?"
        r"\s*[:\-]?\s*"
        r"([0-9]+[.,][0-9]{2})"
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

        if text == "total" or text.startswith("total ") or "total (rm)" in text:

            # Angka dalam box yang sama
            match = re.search(
                r"(\d+[.,]\d{2})",
                item["text"]
            )

            if match:
                return match.group(1)

            # Angka pada box setelahnya
            if i + 1 < len(ocr_results):
                match = re.search(
                    r"(\d+[.,]\d{2})",
                    ocr_results[i + 1]["text"]
                )

                if match:
                    return match.group(1)

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

        return {
            "invoice_number": find_invoice_number(text),
            "date": find_invoice_date(text),
            "total_amount": total,
            "raw_text": raw_text or None
        }

    if document_type == "REAL_LIFE":
        return {
            "raw_text": raw_text or None
        }

    return {}
