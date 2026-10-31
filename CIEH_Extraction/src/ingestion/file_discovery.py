from pathlib import Path

def find_raw_files_paths(extenstions, raw_data_directory):
    raw_data_paths = []
    for item in raw_data_directory.rglob("*"):
        if item.is_dir():
            continue
        else:
            if item.suffix.lower() in extenstions:
                raw_data_paths.append(item)

    return raw_data_paths