import cv2
from config import CROP_PADDING, RESIZE_WIDTH, RESIZE_HEIGHT


def crop_plate(image, box):
    """
    Crops YOLO bounding box with padding + resizing.
    """
    x1, y1, x2, y2, _ = box

    h, w = image.shape[:2]

    x1 = max(0, x1 - CROP_PADDING)
    y1 = max(0, y1 - CROP_PADDING)
    x2 = min(w, x2 + CROP_PADDING)
    y2 = min(h, y2 + CROP_PADDING)

    crop = image[y1:y2, x1:x2]

    crop = cv2.resize(crop, (RESIZE_WIDTH, RESIZE_HEIGHT))

    return crop