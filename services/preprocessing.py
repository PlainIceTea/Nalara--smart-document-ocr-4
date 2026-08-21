import cv2


def preprocess_image(image, max_side=1600):
    """Preprocessing ringan: resize jika gambar terlalu besar."""
    if image is None:
        raise ValueError("Image tidak boleh None.")

    height, width = image.shape[:2]
    scale = min(1.0, max_side / max(height, width))

    if scale < 1.0:
        image = cv2.resize(
            image,
            (int(width * scale), int(height * scale)),
            interpolation=cv2.INTER_AREA
        )

    return image
