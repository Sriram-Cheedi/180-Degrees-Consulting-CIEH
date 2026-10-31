from pathlib import Path

def get_file_metadata(file_path):
    file_metadata = {}
    file_metadata.update({
        "filename" : file_path.name,
        "file_path" : str(file_path),
        "extension" : file_path.suffix.lower(),
        "file_size" : file_path.stat().st_size,
        "council_name": None
    })
    return file_metadata


def get_response_group(file_path, raw_data_directory):
    file_path = file_path.resolve()
    raw_data_directory = raw_data_directory.resolve()

    if file_path.parent == raw_data_directory:
        return f"file:{file_path.name}"
    else:
        return f"folder:{file_path.parts[len(file_path.parts) - 2]}"


def identify_files(file_paths, raw_data_directory):
    source_number = 1
    response_number = 1
    files_metadata = []
    response_groups = {}

    for file_path in file_paths:
        file_metadata = get_file_metadata(file_path)
        file_source_group = get_response_group(file_path, raw_data_directory)

        if file_source_group in response_groups:
            response_id = response_groups[file_source_group]
        else:
            response_id = f"Response_{response_number:03d}"
            response_number+=1
            response_groups.update({
            file_source_group : response_id,
            })

        file_metadata.update({
            "source_id" : f"Source_{source_number:03d}",
            "response_id" : response_id
        })

        source_number += 1
        files_metadata.append(file_metadata)

    return files_metadata



        


