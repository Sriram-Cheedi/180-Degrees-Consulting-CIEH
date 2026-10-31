from pathlib import Path
from rapidocr import RapidOCR
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions

ocr_engine = RapidOCR()

pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = True
pipeline_options.do_table_structure = True
pipeline_options.ocr_options = RapidOcrOptions()

pdf_converter = DocumentConverter(format_options = {
    InputFormat.PDF: PdfFormatOption(pipeline_options = pipeline_options)
})

def read_image(file_path):
    file_path = Path(file_path)
    result = ocr_engine(str(file_path))

    if result.txts is not None:
        lines = list(result.txts)
    else:
        lines = []

    if result.scores is not None:
        scores = list(result.scores)
    else:
        scores = []

    if result.boxes is not None:
        boxes = result.boxes.tolist()
    else:
        boxes = []

    content = "\n".join(lines)

    image_data = {
        "text" : content,
        "lines" : lines,
        "scores" : scores,
        "boxes" : boxes
    }
    return image_data

def read_image_with_docling(file_path):
    result = pdf_converter.convert(Path(file_path))

    return {
        "content": result.document.export_to_markdown(),
        "structure": result.document.export_to_dict(),
        "tables_detected": len(result.document.tables)
    }

def parse_image(file_metadata):
    file_path = file_metadata.get("file_path")
    extension = file_metadata.get("extension")

    if extension not in [".png", ".jpg", ".jpeg"]:
        raise ValueError(f"Unsupported image format: {extension}")

    try:
        result = read_image_with_docling(file_path)

        if not result["content"].strip():
            raise ValueError("Docling returned empty content")

        parsed_data = {
            "source_id": file_metadata.get("source_id"),
            "response_id": file_metadata.get("response_id"),
            "filename": file_metadata.get("filename"),
            "file_type": extension,
            "content": result["content"],
            "structure": result["structure"],
            "tables_detected": result["tables_detected"],
            "parser": "docling",
            "status": "parsed"
        }

    except Exception as error:
        print(f"Docling image parsing failed: {error}")

        result = read_image(file_path)

        parsed_data = {
            "source_id": file_metadata.get("source_id"),
            "response_id": file_metadata.get("response_id"),
            "filename": file_metadata.get("filename"),
            "file_type": extension,
            "content": result["text"],
            "ocr_details": {
                "lines": result["lines"],
                "scores": result["scores"],
                "boxes": result["boxes"]
            },
            "parser": "rapidocr",
            "status": "parsed",
            "review_required": True
        }

    return parsed_data

def read_scanned_pdf(file_path):
    file_path = Path(file_path)
    result = pdf_converter.convert(file_path)
    content = result.document.export_to_markdown()

    return content