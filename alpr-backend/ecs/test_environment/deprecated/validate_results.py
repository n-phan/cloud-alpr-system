import os
import re
import boto3
import pandas as pd
import numpy as np
from datetime import datetime

from fast_plate_ocr import LicensePlateRecognizer
from ultralytics import YOLO
import cv2
from fast_plate_ocr import LicensePlateRecognizer

# YOLO detector
yolo_model = YOLO("../best.pt")

# ---------------- SETTINGS ----------------
IMAGE_DIR = "./samples"
REGION = "us-west-2"

rekognition = boto3.client("rekognition", region_name=REGION)

fast_model = LicensePlateRecognizer(
    "cct-s-v2-global-model",
    providers=["CPUExecutionProvider"]
)

# -----------------------------------------


def geometric_mean_confidence(probs):
    if probs is None or len(probs) == 0:
        return 0.0

    probs = np.array(probs, dtype=np.float64)
    probs = np.clip(probs, 1e-12, 1.0)

    return float(np.exp(np.mean(np.log(probs))))


# ---------------- REKOGNITION ----------------
def run_rekognition(image_path):
    try:
        with open(image_path, "rb") as img:
            response = rekognition.detect_text(Image={"Bytes": img.read()})

        detections = response.get("TextDetections", [])

        candidates = []
        for item in detections:
            text = item.get("DetectedText", "")
            conf = item.get("Confidence", 0)

            cleaned = re.sub(r"[^A-Z0-9]", "", text.upper())

            if 5 <= len(cleaned) <= 8:
                candidates.append((cleaned, conf))

        if candidates:
            best = max(candidates, key=lambda x: x[1])
            return best[0], float(best[1])

        return "NOT_FOUND", 0.0

    except Exception as e:
        print("Rekognition error:", e)
        return "ERROR", 0.0


# ---------------- FAST OCR ----------------
def run_fastocr(image_path):
    try:
        result = fast_model.run(image_path, return_confidence=True)[0]

        plate = result.plate
        #plate = re.sub(r"[^A-Z0-9]", "", str(plate).upper())

        confidence = geometric_mean_confidence(result.char_probs)

        return plate, confidence

    except Exception as e:
        print("Fast OCR error:", e)
        return "ERROR", 0.0


# ---------------- VALIDATION ----------------
def run_validation():
    results = []

    if not os.path.exists(IMAGE_DIR):
        print("samples folder not found")
        return

    files = [
        f for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    for filename in files:

        match = re.search(r"(test\d+)-([A-Z0-9]+)-(\w+)", filename, re.IGNORECASE)
        if not match:
            continue

        test_id, expected, difficulty = match.groups()
        expected = expected.upper()

        path = os.path.join(IMAGE_DIR, filename)

        print(f"Running {filename}")

        # ---------- Rekognition ----------
        rekog_plate, rekog_conf = run_rekognition(path)
        rekog_result = "Pass" if rekog_plate == expected else "Fail"

        # ---------- Fast OCR ----------
        fast_plate, fast_conf = run_fastocr(path)
        fast_result = "Pass" if fast_plate == expected else "Fail"

        results.append({
            "TestID": test_id,
            "Type": difficulty,
            "Expected": expected,

            "Rekog_Actual": rekog_plate,
            "Rekog_Conf": rekog_conf,
            "Rekog_Result": rekog_result,

            "Fast_Actual": fast_plate,
            "Fast_Conf": fast_conf,
            "Fast_Result": fast_result
        })

    df = pd.DataFrame(results)

    if df.empty:
        print("No test images found")
        return

    print("\n================ OCR COMPARISON REPORT ================\n")

    print(df[[
        "TestID",
        "Type",
        "Expected",
        "Rekog_Actual",
        "Rekog_Conf",
        "Rekog_Result",
        "Fast_Actual",
        "Fast_Conf",
        "Fast_Result"
    ]])

    rekog_acc = (df["Rekog_Result"] == "Pass").mean() * 100
    fast_acc = (df["Fast_Result"] == "Pass").mean() * 100

    print("\n---------------------------------------------------")
    print(f"AWS Rekognition Accuracy : {rekog_acc:.1f}%")
    print(f"Fast Plate OCR Accuracy  : {fast_acc:.1f}%")
    print("---------------------------------------------------")

    report = f"ocr_compare_{datetime.now().strftime('%m%d_%H%M')}.csv"
    df.to_csv(report, index=False)

    print(f"\nSaved report: {report}")


if __name__ == "__main__":
    run_validation()