from pathlib import Path

def read_text_file(file_path):
    with Path(file_path).open("r", encoding="utf-8") as file:
        content = file.read()

    return content


def parse_text_file(file_metadata):
    file_path = Path(file_metadata.get("file_path"))
    extract_text = read_text_file(file_path)

    parsed_data = {
        "source_id" : file_metadata.get("source_id"),
        "response_id" : file_metadata.get("response_id"),
        "filename" : file_metadata.get("filename"),
        "file_type" : file_metadata.get("extension"),
        "content" : extract_text,
        "parser" : "python_text",
        "status" : "parsed",
    }

    return parsed_data

