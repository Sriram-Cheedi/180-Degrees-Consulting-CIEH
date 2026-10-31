import json
from src.ai.extraction_prompt import build_extraction_prompt
from src.ai.gemini_client import generate_gemini_extraction


def prepare_document_content(parsed_document: dict) -> str:
    content = parsed_document.get("content")
    if isinstance(content, str):
        return content

    if isinstance(content, (dict, list)):
        return json.dumps(content, ensure_ascii=False)

    raise ValueError("Unsupported or missing document content")


def extract_document(parsed_document: dict) -> dict:
    document_text = prepare_document_content(parsed_document)

    if not document_text.strip():
        raise ValueError("Document content is empty")

    prompt = build_extraction_prompt(document_text)
    extraction = generate_gemini_extraction(prompt)

    return {
        "source_id": parsed_document.get("source_id"),
        "response_id": parsed_document.get("response_id"),
        "filename": parsed_document.get("filename"),
        "source": parsed_document.get("source"),
        "model_provider": "gemini",
        "extraction": extraction.model_dump(),
        "review_status": "pending",
        "validation_status": "schema_valid"
    }
