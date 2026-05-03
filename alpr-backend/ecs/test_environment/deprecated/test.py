from fast_plate_ocr import LicensePlateRecognizer
import numpy as np

def geometric_mean_confidence(probs):
    """
    Compute geometric mean confidence from a list of probabilities.

    Args:
        probs (list or np.array): per-character probabilities (0 to 1)

    Returns:
        float: geometric mean confidence score
    """
    if probs is None or len(probs) == 0:
        return 0.0

    probs = np.array(probs, dtype=np.float64)

    # avoid log(0)
    probs = np.clip(probs, 1e-12, 1.0)

    return float(np.exp(np.mean(np.log(probs))))

m = LicensePlateRecognizer(
    "cct-s-v2-global-model",
    providers=["CPUExecutionProvider"]
)

pred = m.run("test_plate.png", return_confidence=True)[0]

plate = pred.plate
confidence = geometric_mean_confidence(pred.char_probs)

print("Predicted Plate:", plate)
print("Confidence:", confidence)

