from pathlib import Path
from src.review.export_verified_data import export_verified_data

BASE_DIR = Path(__file__).resolve().parent
REVIEW_PATH = BASE_DIR / "data" / "review" / "cieh_review.xlsx"
OUTPUT_DIR = BASE_DIR / "data" / "output"


def finalize_pipeline():
    print("\n=== CIEH FINALISATION ===")

    if not REVIEW_PATH.exists():
        raise FileNotFoundError(f"Review workbook not found: {REVIEW_PATH}")

    total = export_verified_data(REVIEW_PATH, OUTPUT_DIR)
    print(f"\nFinal verified records: {total}")
    print("\n=== FINALISATION COMPLETE ===")

if __name__ == "__main__":
    finalize_pipeline()
