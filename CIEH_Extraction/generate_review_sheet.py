from pathlib import Path
from src.review.export_review_sheet import export_review_sheet

EXTRACTED_DIR = Path("data/extracted")
REVIEW_PATH = Path("data/review/cieh_review.xlsx")

if __name__ == "__main__":
    total = export_review_sheet(EXTRACTED_DIR, REVIEW_PATH)

    print(f"Exported {total} records")
    print(f"Saved to: {REVIEW_PATH}")
