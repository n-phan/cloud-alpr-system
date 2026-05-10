import os
import pandas as pd
import difflib
from worker.processor import process_plate

SAMPLES_FOLDER = "./samples"
REPORT_DIR = "./reports"

os.makedirs(REPORT_DIR, exist_ok=True)

# -----------------------------
# HELPERS
# -----------------------------
def clean(x):
    return "".join(filter(str.isalnum, str(x))).upper()

def parse_filename(file):
    """
    test8-S5239C-medium.jpg
    """
    name = os.path.splitext(file)[0]
    parts = name.split("-")

    if len(parts) != 3:
        return None

    return {
        "test_case": parts[0],
        "expected": clean(parts[1]),
        "category": parts[2].lower()
    }

def normalize_model_output(output):
    """
    Converts process_plate output into list of plate strings
    """
    if output is None:
        return []
    if isinstance(output, str):
        return [clean(output)]
    if isinstance(output, dict):
        return [clean(output.get("plate", ""))]
    if isinstance(output, list):
        plates = []
        for item in output:
            if isinstance(item, dict):
                plates.append(clean(item.get("plate", "")))
            else:
                plates.append(clean(item))
        return plates
    return []

# -----------------------------
# METRICS LOGIC
# -----------------------------
def compute_metrics(expected, predicted_list):
    """
    accuracy: 1 if exact match, else 0
    recall: Correct characters / Total expected characters
    precision: Correct characters / Total predicted characters
    """
    # 1. Accuracy (Right or Wrong at the plate level)
    accuracy = 1 if expected in predicted_list else 0

    # 2. Character-Level Precision and Recall
    if not predicted_list:
        return accuracy, 0.0, 0.0

    best_precision = 0.0
    best_recall = 0.0
    max_matches = -1

    expected_len = len(expected)

    # If the model outputs multiple bounding boxes/plates, 
    # grade the one that has the closest character overlap.
    for pred in predicted_list:
        pred_len = len(pred)
        if pred_len == 0:
            continue

        # Find matching character blocks in sequence
        sm = difflib.SequenceMatcher(None, expected, pred)
        matches = sum(block.size for block in sm.get_matching_blocks())

        r = matches / expected_len if expected_len > 0 else 0.0
        p = matches / pred_len if pred_len > 0 else 0.0

        # Keep the prediction that yields the highest character match
        if matches > max_matches:
            max_matches = matches
            best_recall = r
            best_precision = p
        # Tie-breaker: favor higher precision if match count is identical
        elif matches == max_matches and p > best_precision:
            best_recall = r
            best_precision = p

    return accuracy, best_precision, best_recall

# -----------------------------
# RUN EVALUATION
# -----------------------------
results = []

files = [
    f for f in os.listdir(SAMPLES_FOLDER)
    if f.lower().endswith((".jpg", ".png", ".jpeg"))
]

print(f"Processing {len(files)} images...\n")

for file in files:

    meta = parse_filename(file)
    if not meta:
        continue

    path = os.path.join(SAMPLES_FOLDER, file)

    # -----------------------------
    # REAL MODEL CALL
    # -----------------------------
    output = process_plate(path)
    predicted_list = normalize_model_output(output)

    accuracy, precision, recall = compute_metrics(meta["expected"], predicted_list)

    results.append({
        "file": file,
        "test_case": meta["test_case"],
        "category": meta["category"],
        "expected": meta["expected"],
        "predicted_raw": output,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall
    })

    print(
        f"{file} | expected={meta['expected']} | pred={predicted_list} "
        f"| Acc={accuracy} P={precision:.2f} R={recall:.2f}"
    )

# -----------------------------
# DATAFRAME & AGGREGATION
# -----------------------------
df = pd.DataFrame(results)

df["test_number"] = df["test_case"].str.replace("test", "", regex=False)
df["test_number"] = pd.to_numeric(df["test_number"], errors="coerce")
df = df.sort_values(["category", "test_number"]).drop(columns=["test_number"])

# Global metrics (Macro-average across all images)
global_accuracy = df["accuracy"].mean()
global_precision = df["precision"].mean()
global_recall = df["recall"].mean()

# Category metrics
category_summary = df.groupby("category").agg(
    total=("file", "count"),
    accuracy=("accuracy", "mean"),
    avg_precision=("precision", "mean"),
    avg_recall=("recall", "mean")
).reset_index()

# Format percentages for cleaner CSV outputs
category_summary["accuracy"] = (category_summary["accuracy"] * 100).round(2)
category_summary["avg_precision"] = (category_summary["avg_precision"] * 100).round(2)
category_summary["avg_recall"] = (category_summary["avg_recall"] * 100).round(2)

# -----------------------------
# SAVE REPORTS
# -----------------------------
df.to_csv(f"{REPORT_DIR}/full_results.csv", index=False)
category_summary.to_csv(f"{REPORT_DIR}/category_summary.csv", index=False)

# -----------------------------
# OUTPUT
# -----------------------------
print("\n========================================")
print("GLOBAL METRICS (CHARACTER-LEVEL ALPR)")
print("========================================")

print(f"Accuracy  (Exact Match) : {global_accuracy:.2%}")
print(f"Precision (Valid Chars) : {global_precision:.2%}")
print(f"Recall    (Found Chars) : {global_recall:.2%}")

print("\n========================================")
print("CATEGORY BREAKDOWN (%)")
print("========================================")

print(category_summary.to_string(index=False))

print("\nSaved to:", REPORT_DIR)