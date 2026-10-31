
import json
from pathlib import Path


def save_parsed_file(parsed_data, parsed_directory, file_metadata=None):
    parsed_directory = Path(parsed_directory)
    parsed_directory.mkdir(parents=True, exist_ok=True)
    file_hash = file_metadata.get("file_hash")

    if not file_hash:
        raise ValueError("File hash is missing from metadata")
    output_path = parsed_directory / f"{file_hash}.json"
    saved_data = parsed_data.copy()

    if file_metadata is not None:
        saved_data["source"] = {
            "original_filename": file_metadata.get("filename"),
            "relative_path": file_metadata.get("relative_path"),
            "file_path": file_metadata.get("file_path"),
            "file_hash": file_metadata.get("file_hash"),
            "response_id": file_metadata.get("response_id"),
            "file_size": file_metadata.get("file_size")
        }

    if output_path.exists():
        print(f"Already parsed: {output_path.name}")
        return output_path
    
    with output_path.open("x", encoding="utf-8") as file:
        json.dump(parsed_data, file, indent=4, ensure_ascii=False)
    return output_path


def save_all_parsed_files(parsed_files, parsed_directory, files_metadata=None):
    saved_paths = []
    metadata_lookup = {}

    if files_metadata is not None:
        for metadata in files_metadata:
            metadata_lookup[metadata["source_id"]] = metadata

    for parsed_data in parsed_files:
        source_id = parsed_data["source_id"]
        file_metadata = metadata_lookup.get(source_id)
        saved_path = save_parsed_file(parsed_data, parsed_directory, file_metadata)
        saved_paths.append(saved_path)

    return saved_paths


def load_parsed_file(file_path):
    file_path = Path(file_path)
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)
