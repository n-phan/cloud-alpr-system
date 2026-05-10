import re
import numpy as np
from fast_plate_ocr import LicensePlateRecognizer
from config import FAST_OCR_MODEL, FAST_OCR_PROVIDERS, ZERO_PROB_THRESHOLD


model = LicensePlateRecognizer(
    FAST_OCR_MODEL,
    providers=FAST_OCR_PROVIDERS
)

print("Fast Plate OCR model loaded:", FAST_OCR_MODEL)


def geometric_mean_confidence(probs):
    try:
        if probs is None:
            return 0.0

        probs = np.array(probs, dtype=np.float64)

        if probs.size == 0:
            return 0.0

        probs = np.clip(probs, ZERO_PROB_THRESHOLD, 1.0)

        return float(np.exp(np.mean(np.log(probs))))

    except Exception as e:
        print("[CONFIDENCE ERROR]", e)
        return 0.0


def recognize_plate(image, debug=False):
    """
    Input: cropped image (numpy array)
    Output: (plate, confidence)
    """

    try:
        # -------------------------
        # 1. Validate input
        # -------------------------
        if image is None:
            if debug:
                print("[OCR] Image is None")
            return "NOT_FOUND", 0.0

        if hasattr(image, "size") and image.size == 0:
            if debug:
                print("[OCR] Empty image")
            return "NOT_FOUND", 0.0

        # -------------------------
        # 2. Run OCR safely
        # -------------------------
        result = model.run(image, return_confidence=True)

        if not result:
            if debug:
                print("[OCR] No result returned")
            return "NOT_FOUND", 0.0

        pred = result[0]

        # -------------------------
        # 3. Extract plate safely
        # -------------------------
        raw_plate = getattr(pred, "plate", None)

        if raw_plate is None:
            if debug:
                print("[OCR] Missing plate field")
            return "NOT_FOUND", 0.0

        plate = re.sub(r"[^A-Z0-9]", "", str(raw_plate).upper())

        if not plate:
            if debug:
                print("[OCR] Plate empty after cleaning:", raw_plate)
            return "NOT_FOUND", 0.0

        # -------------------------
        # 4. Confidence safely
        # -------------------------

        char_probs = getattr(pred, "char_probs", None)
        confidence = geometric_mean_confidence(char_probs)
        #print(f"[OCR] Raw plate: {raw_plate}, Cleaned plate: {plate}, Char_Probs: {char_probs}, Confidence: {confidence:.4f}")
        if debug:
            print(f"[OCR] Plate={plate}, Confidence={confidence:.4f}")

        return plate, confidence

    except Exception as e:
        print("[OCR FATAL ERROR]", e)
        return "ERROR", 0.0