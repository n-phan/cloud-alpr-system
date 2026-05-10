import cv2
import numpy as np
from config import CROP_PADDING, RESIZE_WIDTH, RESIZE_HEIGHT


def crop_plate(image, box, debug=False):
    """
    Crops YOLO bounding box with padding + resizing.
    Adds safety checks + debug logging.
    """

    try:
        # -----------------------------
        # 1. Validate inputs
        # -----------------------------
        if image is None:
            if debug:
                print("[CROP] ERROR: image is None")
            return None

        if box is None or len(box) < 4:
            if debug:
                print(f"[CROP] ERROR: invalid box -> {box}")
            return None

        x1, y1, x2, y2, *rest = box

        h, w = image.shape[:2]

        # -----------------------------
        # 2. Clamp coordinates safely
        # -----------------------------
        x1 = max(0, int(x1 - CROP_PADDING))
        y1 = max(0, int(y1 - CROP_PADDING))
        x2 = min(w, int(x2 + CROP_PADDING))
        y2 = min(h, int(y2 + CROP_PADDING))

        # -----------------------------
        # 3. Validate crop region
        # -----------------------------
        if x1 >= x2 or y1 >= y2:
            if debug:
                print(f"[CROP] INVALID REGION: {(x1, y1, x2, y2)}")
            return None

        # -----------------------------
        # 4. Crop safely
        # -----------------------------
        crop = image[y1:y2, x1:x2]

        if crop.size == 0:
            if debug:
                print("[CROP] EMPTY CROP RESULT")
            return None

        # -----------------------------
        # 5. Resize safely
        # -----------------------------
        crop = cv2.resize(crop, (RESIZE_WIDTH, RESIZE_HEIGHT))

        if debug:
            print(f"[CROP] OK -> {crop.shape} from box {(x1, y1, x2, y2)}")

        return crop

    except Exception as e:
        if debug:
            print(f"[CROP] EXCEPTION: {e}")
        return None