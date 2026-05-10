import cv2
from ultralytics import YOLO
from config import YOLO_MODEL_PATH, YOLO_CONF_THRESHOLD

model = YOLO(YOLO_MODEL_PATH)


def detect_plates(image_path):
    """
    Runs YOLO and returns bounding boxes for license plates.
    Output: list of (x1, y1, x2, y2, conf)
    """
    image = cv2.imread(image_path)
    results = model(image)[0]

    boxes = []

    for box in results.boxes:
        conf = float(box.conf[0])

        if conf < YOLO_CONF_THRESHOLD:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        boxes.append((x1, y1, x2, y2, conf))

    return image, boxes