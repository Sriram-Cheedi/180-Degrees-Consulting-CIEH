import hashlib
from pathlib import Path

def calculate_file_hash(file_path):
    hash256 = hashlib.sha256()

    with Path(file_path).open('rb') as file:
        while True:
            chunk = file.read(8192)
            if not chunk:
                break
            hash256.update(chunk)

    return hash256.hexdigest()

def detect_duplicate_files(files_metadata):
    seen_hashes = {}

    for file_metadata in files_metadata:
        file_path = file_metadata.get("file_path")
        file_hash = calculate_file_hash(file_path)
        file_metadata["file_hash"] = file_hash

        if file_hash in seen_hashes:
            file_metadata["is_duplicate"] = True
            file_metadata["duplicate_of"] = seen_hashes[file_hash]
        else:
            file_metadata["is_duplicate"] = False
            file_metadata["duplicate_of"] = None
            seen_hashes[file_hash] = file_metadata.get("source_id")

    return files_metadata

def get_unique_file(files_metadata):
    unique_files_meta_data = []
    for file_metadata in files_metadata:
        if not file_metadata.get("is_duplicate"):
            unique_files_meta_data.append(file_metadata)

    return unique_files_meta_data

