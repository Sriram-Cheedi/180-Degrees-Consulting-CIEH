
import json
from pathlib import Path


def save_extraction(extraction_data: dict, output_directory: Path) -> Path:
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    source = extraction_data.get("source") or {}
    file_hash = source.get("file_hash")

    if not file_hash:
        raise ValueError("Missing source file hash")

    output_path = output_directory / f"{file_hash}.json"

    if output_path.exists():
        raise FileExistsError(f"Extraction already exists: {output_path}")

    with output_path.open("x", encoding="utf-8") as file:
        json.dump(extraction_data, file, indent=4, ensure_ascii=False)

    return output_path
