"""
Ingest Neo4j folder data into Langent vector DB
"""
import csv
import os
import sys
import urllib.request
import json

NEO4J_DIR = r"c:\Users\daewooenc\workspace\Ontology\Neo4J"

# 1. Check CSV structure
data_csv = os.path.join(NEO4J_DIR, "data", "소상공인시장진흥공단_상가(상권)정보_서울_202512.csv")

for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
    try:
        with open(data_csv, "r", encoding=enc) as f:
            reader = csv.reader(f)
            header = next(reader)
            row = next(reader)
            print(f"Encoding: {enc} ✓")
            print(f"Columns ({len(header)}):")
            for i, h in enumerate(header[:20]):
                print(f"  {i}: {h} = {row[i] if i < len(row) else ''}")
            print(f"  ... {len(header)} total columns")
            break
    except Exception as e:
        print(f"Encoding {enc} failed: {e}")

# 2. Count rows
print("\nCounting rows in Seoul data...")
count = 0
with open(data_csv, "r", encoding=enc) as f:
    for _ in f:
        count += 1
print(f"  Seoul rows: {count:,}")

# 3. List all CSV files
print("\nAll CSV files:")
csv_dir = os.path.join(NEO4J_DIR, "소상공인시장진흥공단_상가(상권)정보_20251231")
if os.path.exists(csv_dir):
    for fname in sorted(os.listdir(csv_dir)):
        if fname.endswith(".csv"):
            fpath = os.path.join(csv_dir, fname)
            size_mb = os.path.getsize(fpath) / 1024 / 1024
            print(f"  {fname} ({size_mb:.1f} MB)")
