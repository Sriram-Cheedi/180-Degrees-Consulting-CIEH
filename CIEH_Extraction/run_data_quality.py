import csv
from pathlib import Path
from src.validation.data_quality import audit_extractions

EXTRACTED_DIR = Path("data/extracted")
OUTPUT_PATH = Path("data/review/data_quality_issues.csv")

def run_quality_audit():
    summary, issues = audit_extractions(EXTRACTED_DIR)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "record_id",
                "filename",
                "issue_type",
                "message"
            ]
        )

        writer.writeheader()
        writer.writerows(issues)

    print("\n=== DATA QUALITY SUMMARY ===")

    for key, value in summary.items():
        print(f"{key}: {value}")

    print(f"\nSaved report: {OUTPUT_PATH}")

    issue_counts = {}

    for issue in issues:
        issue_type = issue["issue_type"]
        issue_counts[issue_type] = (issue_counts.get(issue_type, 0) + 1)

    print("\nIssues by type:")

    for issue_type, count in sorted(issue_counts.items()):
        print(f"{issue_type}: {count}")


if __name__ == "__main__":
    run_quality_audit()
