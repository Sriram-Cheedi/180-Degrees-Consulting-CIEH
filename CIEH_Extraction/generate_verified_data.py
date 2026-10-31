from pathlib import Path
from src.review.export_verified_data import export_verified_data

REVIEW_FILE = Path("data/review/cieh_review.xlsx")
OUTPUT_DIR = Path("data/output")

if __name__ == "__main__":
    total = export_verified_data(REVIEW_FILE, OUTPUT_DIR)
    print(f"\nFinished. Exported {total} verified records.")
