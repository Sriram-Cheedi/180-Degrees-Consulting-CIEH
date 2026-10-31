import subprocess
import sys
from pathlib import Path
from src.ai.batch_extraction import extract_all_documents
from src.review.sync_review_sheet import sync_review_sheet
from run_data_quality import run_quality_audit

BASE_DIR = Path(__file__).resolve().parent
PARSED_DIR = BASE_DIR / "data" / "parsed"
EXTRACTED_DIR = BASE_DIR / "data" / "extracted"
REVIEW_PATH = BASE_DIR / "data" / "review" / "cieh_review.xlsx"

def run_pipeline():
    print("\n=== CIEH EXTRACTION PIPELINE ===", flush=True)

    # Step 1 — Parse raw FOI files
    print("\n[1/4] Discovering and parsing files...", flush=True)

    subprocess.run(
        [sys.executable, str(BASE_DIR / "parse_pipeline.py")],
        cwd=BASE_DIR,
        check=True
    )

    # Step 2 — Extract using Gemini
    print("\n[2/4] Running Gemini extraction...", flush=True)

    summary = extract_all_documents(
        PARSED_DIR,
        EXTRACTED_DIR
    )

    print("Extraction summary:", summary)

    # Step 3 — Check extracted data
    print("\n[3/4] Running quality checks...", flush=True)

    run_quality_audit()

    # Step 4 — Generate review sheet
    
    # Step 4 — Synchronise Excel review sheet
    print("\n[4/4] Synchronising review sheet...", flush=True)

    review_summary = sync_review_sheet(
        EXTRACTED_DIR,
        REVIEW_PATH
    )

    print("Review summary:", review_summary)


    print("\n=== PIPELINE FINISHED ===")


if __name__ == "__main__":
    run_pipeline()
