import os
import re
import boto3
import pandas as pd
from datetime import datetime

# --- SETTINGS ---
IMAGE_DIR = "./samples"
TABLE_NAME = "GateEvents"
REGION = "us-west-2"

dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

def run_validation():
    results = []
    
    if not os.path.exists(IMAGE_DIR):
        print(f"Error: {IMAGE_DIR} folder not found.")
        return

    # 1. Read local folder
    files = [f for f in os.listdir(IMAGE_DIR) if f.endswith(('.jpg', '.png', '.jpeg'))]
    
    # 2. Get all items from DynamoDB (Scan) 
    print("Fetching records from DynamoDB...")
    try:
        response = table.scan()
        items = response.get('Items', [])
    except Exception as e:
        print(f"Failed to scan DynamoDB: {e}")
        return

    for filename in files:
        # Regex: test1-abc1234-easy.jpg
        # Groups: 1=test1, 2=abc1234, 3=easy
        match = re.search(r"(test\d+)-([A-Z0-9]+)-(\w+)", filename, re.IGNORECASE)
        if not match: continue

        test_label, expected, test_type = match.groups()
        expected = expected.upper()
        
        print(f"Matching #{test_label} | Type: {test_type}...")

        actual = "NOT_FOUND"
        confidence = 0.0
        status = "Fail"
        found_url = "N/A"

        # 3. Suffix Match Logic
        for item in items:
            db_url = item.get('image_url', '')
            if db_url.endswith(filename):
                actual = item.get('plate_text', 'N/A').upper()
                # Get confidence (default to 0.0 if missing)
                confidence = item.get('confidence', 0.0)
                found_url = db_url
                
                if actual == expected:
                    status = "Pass"
                break 

        # 4. Generate structured result
        results.append({
            "TestID": test_label,
            "Type": test_type,
            "Expected": expected,
            "Actual": actual,
            "Confidence": float(confidence),
            "Result": status,
            "Full_URL": found_url
        })

    # 5. Final Report & Metrics
    df = pd.DataFrame(results)
    
    if not df.empty:
        print("\n" + "="*60)
        print(f"              ALPR TEST EXECUTION REPORT")
        print("="*60)
        # Displaying Type and Confidence in the console output
        print(df[['TestID', 'Type', 'Expected', 'Actual', 'Confidence', 'Result']])
        print("-" * 60)
        
        overall_acc = (df['Result'] == "Pass").mean() * 100
        avg_conf = df[df['Actual'] != "NOT_FOUND"]['Confidence'].mean()
        
        print(f"Overall Accuracy: {overall_acc:.1f}%")
        print(f"Average Confidence: {avg_conf:.2f}")
        
        # Save to CSV
        report_file = f"alpr_detailed_results_{datetime.now().strftime('%m%d_%H%M')}.csv"
        df.to_csv(report_file, index=False)
        print(f"\nDetailed report saved: {report_file}")
    else:
        print("No matches found. Ensure local filenames match the end of S3 URLs.")

if __name__ == "__main__":
    run_validation()