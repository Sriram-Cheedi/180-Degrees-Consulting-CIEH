from src.parsing.text_parser import parse_text_file
from src.parsing.spreadsheet_parser import parse_spreadsheet
from src.parsing.document_parser import parse_document
from src.parsing.ocr_parser import parse_image, read_scanned_pdf


def parse_file(file_metadata):
    extension = file_metadata.get("extension")

    if extension == ".txt":
        return parse_text_file(file_metadata)
    elif extension in [".csv", ".xlsx", ".xls"]:
        return parse_spreadsheet(file_metadata)
    elif extension in [".pdf", ".docx"]:
        if extension == ".pdf":
            content = read_scanned_pdf(file_metadata.get("file_path"))

            return {
                "source_id": file_metadata.get("source_id"),
                "response_id": file_metadata.get("response_id"),
                "filename": file_metadata.get("filename"),
                "file_type": extension,
                "content": content,
                "parser": "docling_rapidocr",
                "status": "parsed"
            }

        return parse_document(file_metadata)
    elif extension in [".png", ".jpg", ".jpeg"]:
        return parse_image(file_metadata)
    else:
        raise ValueError(f"Unsupported file format: {extension}")


def parse_all_files(files_metadata):
    parsed_files = []

    for file_metadata in files_metadata:
        try:
            print(f"Processing: {file_metadata['filename']}", flush=True)
            file_metadata["status"] = "processing"
            parsed_data = parse_file(file_metadata)
            parsed_files.append(parsed_data)
            file_metadata["status"] = "completed"

        except Exception as error:
            file_metadata["status"] = "failed"
            file_metadata["error"] = str(error)

            print(f"Failed to parse {file_metadata.get('filename')}: {error}")

    return parsed_files
