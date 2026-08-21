import time
import cv2
import numpy as np
import pandas as pd
import streamlit as st

from services.preprocessing import preprocess_image
from services.ocr_service import run_ocr
from services.extraction import extract_fields
from services.validation import validate_document

st.set_page_config(page_title="Smart Document OCR & Validation", page_icon="📄", layout="wide")
st.title("📄 Smart Document OCR & Validation")
st.caption("Upload dokumen → OCR → Extraction → Validation")

DOCUMENT_TYPES = ["DOCUMENT", "FORM", "INVOICE", "REAL_LIFE"]

def uploaded_file_to_cv2(uploaded_file):
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("File gambar tidak dapat dibaca.")
    return image

def draw_ocr_boxes(image, ocr_results):
    output = image.copy()
    for item in ocr_results:
        bbox = np.array(item["box"], dtype=np.int32)
        cv2.polylines(output, [bbox], True, (0, 255, 0), 2)
        x, y = bbox[0]
        label = f'{item["text"]} ({item["confidence"]:.2f})'
        cv2.putText(output, label[:45], (int(x), max(20, int(y)-5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 180, 0), 1, cv2.LINE_AA)
    return output

document_type = st.selectbox("Jenis dokumen", DOCUMENT_TYPES)
uploaded_file = st.file_uploader("Upload dokumen", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    try:
        image = uploaded_file_to_cv2(uploaded_file)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Dokumen Asli")
            st.image(cv2.cvtColor(image, cv2.COLOR_BGR2RGB), use_container_width=True)

        if st.button("🔍 Process Document", type="primary"):
            with st.spinner("Memproses dokumen..."):
                start = time.perf_counter()
                processed = preprocess_image(image)
                ocr_results = run_ocr(processed)

                raw_text = "\n".join(item["text"] for item in ocr_results)
                avg_confidence = (
                    float(np.mean([item["confidence"] for item in ocr_results]))
                    if ocr_results else 0.0
                )

                extracted = extract_fields(document_type, raw_text, ocr_results)
                validation = validate_document(
                    document_type, extracted, avg_confidence, raw_text
                )

                elapsed = time.perf_counter() - start
                visualized = draw_ocr_boxes(processed, ocr_results)

            with col2:
                st.subheader("Hasil OCR")
                st.image(cv2.cvtColor(visualized, cv2.COLOR_BGR2RGB), use_container_width=True)

            st.divider()

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Status", validation["status"])
            m2.metric("OCR Confidence", f"{avg_confidence:.2%}")
            m3.metric("Text Box", len(ocr_results))
            m4.metric("Processing Time", f"{elapsed:.2f} s")

            left, right = st.columns(2)

            with left:
                st.subheader("Extracted Information")
                extracted_df = pd.DataFrame([
                    {"Field": k, "Value": v if v else "-"}
                    for k, v in extracted.items()
                ])
                st.dataframe(extracted_df, hide_index=True, use_container_width=True)

                if validation["missing_fields"]:
                    st.warning("Missing field: " + ", ".join(validation["missing_fields"]))
                st.caption(validation["reason"])

            with right:
                st.subheader("Raw OCR Text")
                st.text_area("OCR Result", raw_text or "Tidak ada teks terdeteksi.", height=260)

            with st.expander("Detail OCR"):
                detail_df = pd.DataFrame([
                    {"text": item["text"], "confidence": round(item["confidence"], 4)}
                    for item in ocr_results
                ])
                if len(detail_df):
                    st.dataframe(detail_df, hide_index=True, use_container_width=True)
                else:
                    st.info("Tidak ada hasil OCR.")

    except Exception as error:
        st.error(f"Terjadi error: {error}")
