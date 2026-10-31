
import json
from pathlib import Path

from src.ai.extraction_service import extract_document
from src.ai.save_extraction import save_extraction


def extract_all_documents(parsed_directory: Path, extracted_directory: Path) -> dict:
    parsed_directory = Path(parsed_directory)
    extracted_directory = Path(extracted_directory)
    extracted_directory.mkdir(parents=True,exist_ok=True)

    summary = {
        "total": 0,
        "completed": 0,
        "skipped": 0,
        "failed": 0,
        "errors": []
    }

    for file_path in sorted(parsed_directory.glob("*.json")):
        summary["total"] += 1
        try:
            # Read parsed document
            with file_path.open("r", encoding="utf-8") as file:
                parsed_document = json.load(file)

            # Get SHA-256 hash of original document
            source = parsed_document.get("source") or {}

            file_hash = source.get("file_hash")

            if not file_hash:
                file_hash = file_path.stem

            parsed_document["source"] = {**source, "file_hash": file_hash}

            # Each original document has one extraction JSON
            output_path = extracted_directory / f"{file_hash}.json"

            # Skip files already extracted
            if output_path.exists():
                summary["skipped"] += 1
                print(f"Skipped: {file_path.name}")
                continue

            print(f"Extracting: {file_path.name}", flush=True)

            # Gemini extraction + Pydantic validation
            extraction_data = extract_document(parsed_document)

            # Save the structured JSON
            save_extraction(extraction_data,extracted_directory)

            summary["completed"] += 1
            print(f"Completed: {file_path.name}")

        except Exception as error:
            summary["failed"] += 1
            summary["errors"].append({"file": file_path.name, "error": str(error)})
            print(f"Failed: {file_path.name} — {error}")

    return summary
