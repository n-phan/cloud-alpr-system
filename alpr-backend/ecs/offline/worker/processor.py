from ml.yolo_detector import detect_plates
from preprocessing.cropper import crop_plate
from ml.fast_plate import recognize_plate


def process_plate(image_path):
    image, boxes = detect_plates(image_path)

    results = []

    for box in boxes:
        crop = crop_plate(image, box)
        plate, conf = recognize_plate(crop)

        results.append({
            "plate": plate,
            "confidence": conf
        })

    return results