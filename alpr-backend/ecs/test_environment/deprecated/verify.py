import os
import boto3
import pandas as pd
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

# -----------------------------
# CONFIG
# -----------------------------
SAMPLES_FOLDER = "./samples"
TABLE_NAME = "GateEvents"
REGION = "us-west-2"
REPORT_DIR = "./reports"
PLATE_TEXT_FIELD = "plate_text"

# -----------------------------
# ENSURE REPORT DIR EXISTS
# -----------------------------
os.makedirs(REPORT_DIR, exist_ok=True)

# -----------------------------
# DYNAMODB SETUP
# -----------------------------
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

print(f"Connected to DynamoDB table: {TABLE_NAME} in region {REGION}")

# -----------------------------
# STORAGE
# -----------------------------
results = []

# -----------------------------
# HELPERS
# -----------------------------
def normalize(text):
    return str(text).strip().upper()

# -----------------------------
# PROCESS FILES
# -----------------------------
for filename in os.listdir(SAMPLES_FOLDER):

    filepath = os.path.join(SAMPLES_FOLDER, filename)
    if not os.path.isfile(filepath):
        continue

    name = os.path.splitext(filename)[0]
    parts = name.split("-")

    if len(parts) < 3:
        print(f"Skipping invalid format: {filename}")
        continue

    test_case = parts[0]
    category = parts[2]

    try:
        test_number = int(test_case.replace("test", ""))
    except:
        test_number = -1

    expected_plate = normalize(parts[1])

    try:
        response = table.scan(
            FilterExpression=Attr(PLATE_TEXT_FIELD).eq(expected_plate)
        )

        items = response.get("Items", [])

        if items:
            db_plate = normalize(items[0].get("plate_text", ""))
            confidence = items[0].get("confidence") or items[0].get("conf")
        else:
            db_plate = "NOT_FOUND"
            confidence = None

        match = (db_plate == expected_plate)

        results.append({
            "test_case": test_case,
            "test_number": test_number,
            "category": category,
            "expected_plate": expected_plate,
            "actual_plate": db_plate,
            "confidence": confidence,
            "pass": match
        })

        print(f"{filename} | expected={expected_plate} | actual={db_plate} | conf={confidence} | PASS={match}")

    except ClientError as e:
        print(f"ERROR: {e.response['Error']['Message']}")

# -----------------------------
# DATAFRAME
# -----------------------------
df = pd.DataFrame(results)
df = df.sort_values(by=["category", "test_number"])

# -----------------------------
# METRICS
# -----------------------------
accuracy = df["pass"].mean()

tp = len(df[df["pass"] == True])
fp = len(df[(df["pass"] == False) & (df["actual_plate"] != "NOT_FOUND")])
fn = len(df[df["actual_plate"] == "NOT_FOUND"])

precision = tp / (tp + fp + 1e-9)
recall = tp / (tp + fn + 1e-9)

# -----------------------------
# CATEGORY METRICS
# -----------------------------
category_summary = df.groupby("category")["pass"].agg(
    total="count",
    correct="sum",
    accuracy="mean"
).reset_index()

category_summary["accuracy_pct"] = (category_summary["accuracy"] * 100).round(2)
category_summary = category_summary.sort_values("accuracy")

# -----------------------------
# FAILED CASES
# -----------------------------
failed_df = df[df["pass"] == False].sort_values(by=["category", "test_number"])

# -----------------------------
# SAVE TO REPORTS FOLDER
# -----------------------------
df.to_csv(f"{REPORT_DIR}/full_results.csv", index=False)
category_summary.to_csv(f"{REPORT_DIR}/category_summary.csv", index=False)
failed_df.to_csv(f"{REPORT_DIR}/failed_cases.csv", index=False)

metrics_summary = pd.DataFrame([{
    "accuracy": accuracy,
    "precision": precision,
    "recall": recall,
    "mean_confidence": df["confidence"].mean()
}])

metrics_summary.to_csv(f"{REPORT_DIR}/metrics_summary.csv", index=False)

# -----------------------------
# OUTPUT
# -----------------------------
print("\n==============================")
print(f"OVERALL ACCURACY: {accuracy:.2%}")
print(f"PRECISION: {precision:.2%}")
print(f"RECALL: {recall:.2%}")
print("==============================")

print(f"\nReports saved to: {REPORT_DIR}/")