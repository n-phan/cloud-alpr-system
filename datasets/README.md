# Datasets

## Sources

**Kaggle ALPR Dataset**
- URL: https://www.kaggle.com/datasets/mgmitesh/automatic-license-plate-recognition-alpr-dataset
- Status: [ ] Downloaded
- Location: raw/kaggle-alpr/
- Size: ~500MB
- Images: ~4,500 labeled plates

## Processing Pipeline

Raw data → Preprocessed data
- Resize to 640x640
- Convert annotations to YOLO format
- Create train/val/test split (70/15/15)

