from src.ingestion.file_discovery import find_raw_files_paths
from src.ingestion.file_identification import identify_files
from src.ingestion.file_hashing import detect_duplicate_files


def assign_file_status(files_metadata):
    for file_metadata in files_metadata:
        if file_metadata.get("is_duplicate"):
            file_metadata["status"] = "duplicate"
        else:
            file_metadata["status"] = "pending"

    return files_metadata


def prepare_files(raw_data_directory, extensions):
    file_paths = find_raw_files_paths(extensions, raw_data_directory)
    files_metadata = identify_files(file_paths, raw_data_directory)
    files_metadata = detect_duplicate_files(files_metadata)
    files_data = assign_file_status(files_metadata)

    return files_data


def get_pending_files(files_data):
    pending_files = []

    for file_metadata in files_data:
        if file_metadata.get("status") == "pending":
            pending_files.append(file_metadata)

    return pending_files
