import re
import numpy as np
from fast_plate_ocr import LicensePlateRecognizer
from config import FAST_OCR_MODEL, FAST_OCR_PROVIDERS, ZERO_PROB_THRESHOLD


model = LicensePlateRecognizer(
    FAST_OCR_MODEL,
    providers=FAST_OCR_PROVIDERS
)


def geometric_mean_confidence(probs):
    if not probs:
        return 0.0

    probs = np.array(probs, dtype=np.float64)
    probs = np.clip(probs, ZERO_PROB_THRESHOLD, 1.0)

    return float(np.exp(np.mean(np.log(probs))))


def recognize_plate(image):
    """
    Input: cropped image (numpy array)
    Output: (plate, confidence)
    """
    result = model.run(image)

    if not result:
        return "NOT_FOUND", 0.0

    pred = result[0]

    plate = getattr(pred, "plate", "NOT_FOUND")
    plate = re.sub(r"[^A-Z0-9]", "", str(plate).upper())

    confidence = geometric_mean_confidence(getattr(pred, "char_probs", None))

    return plate, confidence