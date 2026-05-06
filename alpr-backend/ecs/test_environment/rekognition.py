import boto3
import re
from config import AWS_REGION

rekognition = boto3.client("rekognition", region_name=AWS_REGION)


def run_rekognition(image_path):
    """
    AWS Rekognition text detection fallback
    """
    try:
        with open(image_path, "rb") as f:
            response = rekognition.detect_text(Image={"Bytes": f.read()})

        detections = response.get("TextDetections", [])

        candidates = []

        for d in detections:
            text = d.get("DetectedText", "")
            conf = d.get("Confidence", 0)

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