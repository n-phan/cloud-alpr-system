#  License Plate Detection & OCR Pipeline (YOLOv8 + EasyOCR)

This project implements an end-to-end pipeline for **license plate detection and text extraction** using:

- **YOLOv8 (Ultralytics)** for object detection  
- **EasyOCR** for optical character recognition  
- **OpenCV** for image preprocessing and visualization  
- **Google Colab + Google Drive** for training and storage  

---

##  Overview

The system performs the following steps:

1. **Dataset parsing & validation**
   - Reads YOLO-format labels
   - Computes class distribution

2. **Model Training (YOLOv8)**
   - Trains a lightweight detection model (`yolov8n`)
   - Detects license plate bounding boxes

3. **Inference / Testing**
   - Runs detection on test images
   - Saves prediction outputs

4. **OCR Pipeline**
   - Crops detected plates
   - Preprocesses images (denoising, resizing, grayscale)
   - Extracts text using EasyOCR

5. **Output Generation**
   - Annotated images with bounding boxes + text
   - JSON results per image

---

##  Dataset Structure

cmpe281_data/
│
├── train/
│   ├── images/
│   └── labels/
│
├── valid/
│   ├── images/
│   └── labels/
│
├── test/
│   ├── images/
│   └── labels/
│
└── data.yaml

---

##  Setup

### 1. Install dependencies

pip install ultralytics easyocr opencv-python numpy

### 2. Mount Google Drive (Colab)

from google.colab import drive
drive.mount('/content/drive')

---

##  Model Training (YOLOv8)

from ultralytics import YOLO

model = YOLO("yolov8n.pt")

model.train(
    data="data.yaml",
    epochs=100,
    imgsz=512,
    batch=16,
    cache="disk",
    workers=2,
    amp=True,
    project="/content/drive/MyDrive/yolo_runs",
    name="exp1",
    save=True,
    save_period=5
)

---

## 🔍 Inference

model = YOLO("best.pt")

model.predict(
    source="test/images",
    conf=0.25,
    save=True
)

---

##  OCR Pipeline

Preprocessing Steps:
- Crop detected plate region  
- Remove border noise  
- Resize image  
- Convert to grayscale  
- Apply bilateral filter  

OCR Execution:

import easyocr
reader = easyocr.Reader(['en'])

result = reader.readtext(image)

---

## 📦 Output Format

{
  "status": "OK",
  "results": [
    {
      "plate": "ABC1234",
      "confidence": 0.87
    }
  ]
}

---

##  Features

- YOLOv8-based license plate detection  
- OCR extraction with filtering & confidence scoring  
- Image preprocessing pipeline for better OCR accuracy  
- Batch inference on dataset  
- Debug visualization for model evaluation  

---

##  Improvements Made

- Enhanced plate cropping (margin correction)  
- Bilateral filtering for noise removal  
- Confidence-based OCR filtering  
- Sorting OCR results by bounding box size  
- Class distribution analysis  

---

##  Future Work

- Real-time webcam detection  
- REST API deployment  
- AWS Rekognition fallback  
- Model optimization  

---

