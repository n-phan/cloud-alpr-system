import os

# -------------------------------
# GENERAL PATHS
# -------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE")

SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
SQS_DLQ_URL = os.getenv("SQS_DLQ_URL")
print("Config loaded: AWS_REGION =", AWS_REGION)
print("Config loaded: DYNAMODB_TABLE =", DYNAMODB_TABLE)
print("Config loaded: SQS_QUEUE_URL =", SQS_QUEUE_URL)
print("Config loaded: SQS_DLQ_URL =", SQS_DLQ_URL)
# -------------------------------
# YOLO CONFIG
# -------------------------------
YOLO_MODEL_PATH = os.path.join(BASE_DIR, "models", "best.pt")
YOLO_CONF_THRESHOLD = 0.5  # filter weak detections


# -------------------------------
# FAST PLATE OCR CONFIG
# -------------------------------
FAST_OCR_MODEL = "cct-s-v2-global-model"
FAST_OCR_PROVIDERS = ["CPUExecutionProvider"]  # switch to CUDA if needed


# -------------------------------
# IMAGE PROCESSING
# -------------------------------
CROP_PADDING = 5  # pixels added around YOLO box
RESIZE_WIDTH = 224
RESIZE_HEIGHT = 224


# -------------------------------
# ALPR FILTERS
# -------------------------------
MIN_PLATE_LEN = 5
MAX_PLATE_LEN = 8


# -------------------------------
# AWS REKOGNITION
# -------------------------------
AWS_REGION = "us-west-2"
USE_REKOGNITION = True


# -------------------------------
# CONFIDENCE SETTINGS
# -------------------------------
ZERO_PROB_THRESHOLD = 1e-12
USE_GEOMETRIC_MEAN = True


# -------------------------------
# VALIDATION / TESTING
# -------------------------------
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")