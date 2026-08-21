REQUIRED_FIELDS = {
    "DOCUMENT": ["document_id", "raw_text"],
    "FORM": ["from", "to"],
    "INVOICE": ["invoice_number", "date", "total_amount"],
    "REAL_LIFE": ["raw_text"]
}


def validate_document(
    document_type,
    extracted_fields,
    avg_confidence,
    raw_text,
    review_threshold=0.60
):
    if not raw_text.strip():
        return {
            "status": "INCOMPLETE",
            "missing_fields": REQUIRED_FIELDS.get(document_type, []),
            "reason": "OCR tidak menemukan teks."
        }

    required = REQUIRED_FIELDS.get(document_type, [])
    missing_fields = [
        field for field in required
        if not extracted_fields.get(field)
    ]

    if missing_fields:
        return {
            "status": "INCOMPLETE",
            "missing_fields": missing_fields,
            "reason": "Terdapat required field yang tidak ditemukan."
        }

    if avg_confidence < review_threshold:
        return {
            "status": "NEEDS REVIEW",
            "missing_fields": [],
            "reason": (
                f"OCR confidence {avg_confidence:.2%} "
                f"di bawah threshold {review_threshold:.0%}."
            )
        }

    return {
        "status": "VALID",
        "missing_fields": [],
        "reason": "Required field lengkap dan OCR confidence mencukupi."
    }
