import os
from yolo_detector import detect_plates
from cropper import crop_plate
from fast_plate import recognize_plate
from rekognition import run_rekognition
from config import IMAGE_DIR, IMAGE_EXTENSIONS


def process_image(image_path):
    image, boxes = detect_plates(image_path)

    results = []

    for box in boxes:
        crop = crop_plate(image, box)
        plate, conf = recognize_plate(crop)
        results.append((plate, conf))

    return results


def run_folder():
    files = [
        f for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith(IMAGE_EXTENSIONS)
    ]

    for f in files:
        path = os.path.join(IMAGE_DIR, f)

        print(f"\nProcessing: {f}")

        plates = process_image(path)
        rekog_plate, rekog_conf = run_rekognition(path)

        print("Fast OCR:", plates)
        print("Rekognition:", rekog_plate, rekog_conf)


if __name__ == "__main__":
    run_folder()