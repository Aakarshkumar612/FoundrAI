import io
import pandas as pd
import math
import re

# Logic from backend.routers.upload and backend.automl.trainer
REQUIRED_COLUMNS = {"revenue", "burn_rate", "headcount", "cac", "ltv"}

def clean_num(val, is_int=False):
    if pd.isna(val): return 0
    s = re.sub(r'[^\d.-]', '', str(val))
    try:
        fval = float(s)
        if math.isnan(fval) or math.isinf(fval): return 0
        return int(fval) if is_int else fval
    except (ValueError, TypeError):
        return 0

def test_upload_logic(name, csv_content):
    print(f"--- Testing {name} ---")
    try:
        df = pd.read_csv(io.BytesIO(csv_content.encode()))
        df.columns = [c.strip().lower() for c in df.columns]
        print(f"  Columns found: {list(df.columns)}")
        
        rows = []
        for _, row in df.iterrows():
            processed_row = {
                "month": str(row.get("month", "")),
                "revenue": clean_num(row.get("revenue")),
                "burn_rate": clean_num(row.get("burn_rate")),
                "headcount": clean_num(row.get("headcount"), is_int=True),
                "cac": clean_num(row.get("cac")),
                "ltv": clean_num(row.get("ltv")),
            }
            rows.append(processed_row)
        
        print(f"  Processed {len(rows)} rows successfully.")
        if len(rows) > 0:
            print(f"  Sample Row: {rows[-1]}")
            # Verify JSON serializability
            import json
            json.dumps(rows)
            print("  ✅ JSON Serialisation Check: OK")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")

# 1. Clean Standard CSV
csv_1 = "month,revenue,burn_rate,headcount,cac,ltv\n2024-01,10000,5000,10,200,1000"
test_upload_logic("Standard Clean CSV", csv_1)

# 2. Messy CSV with Symbols and NaNs
csv_2 = "Month, Revenue, Burn_Rate, Headcount, CAC, LTV\n2024-02,\"$12,000.00\", 6000, 11, , 1200\n2024-03, NaN, 7000, 12, 250, Inf"
test_upload_logic("Messy CSV (Symbols, NaNs, Inf)", csv_2)

# 3. Missing Columns (Kaggle-style)
csv_3 = "Company,Valuation,Country\nGoogle,2T,USA\nNvidia,3T,USA"
test_upload_logic("Kaggle-style (Missing Required Columns)", csv_3)
