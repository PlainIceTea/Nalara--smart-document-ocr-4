import easyocr

_reader = easyocr.Reader(["en"], gpu=False, verbose=False)


def run_ocr(image):
    """
    Contoh Output:
    [
        {
            "text": "...",
            "confidence": 0.95,
            "box": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        }
    ]
    """
    results = _reader.readtext(image, detail=1, paragraph=False)

    output = []
    for bbox, text, confidence in results:
        output.append({
            "text": str(text).strip(),
            "confidence": float(confidence),
            "box": [[int(p[0]), int(p[1])] for p in bbox]
        })

    return output
