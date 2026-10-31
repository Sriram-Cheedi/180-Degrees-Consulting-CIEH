import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from src.ai.extraction_schema import DocumentExtraction

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

MODEL_NAME = os.getenv("GEMINI_MODEL","gemini-3.8-flash")

def generate_gemini_extraction(prompt: str) -> DocumentExtraction:
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_json_schema=DocumentExtraction.model_json_schema()
        )
    )

    if not response.text:
        raise ValueError("Gemini returned an empty response")

    return DocumentExtraction.model_validate_json(response.text)
