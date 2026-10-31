from pathlib import Path
from docling.document_converter import DocumentConverter

converter = DocumentConverter()

def read_document(file_path):
    file_path = Path(file_path)
    result = converter.convert(file_path)
    content = result.document.export_to_markdown()
    return content

def get_document_structure(file_path):
    file_path = Path(file_path)

    result = converter.convert(file_path)

    structure = result.document.export_to_dict()

    return structure

def parse_document(file_metadata):
    file_path = file_metadata.get("file_path")
    extension = file_metadata.get("extension")

    if extension not in [".pdf", ".docx"]:
        raise ValueError(f"Unsupported document format: {extension}")

    content = read_document(file_path)

    parsed_data = {
        "source_id": file_metadata.get("source_id"),
        "response_id": file_metadata.get("response_id"),
        "filename": file_metadata.get("filename"),
        "file_type": extension,
        "content": content,
        "parser": "docling",
        "status": "parsed"
    }

    return parsed_data