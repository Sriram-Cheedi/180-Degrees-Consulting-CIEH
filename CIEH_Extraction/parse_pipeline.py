from pathlib import Path
from src.ingestion.file_manager import prepare_files, get_pending_files
from src.parsing.file_parser import parse_all_files
from src.parsing.save_parsed import save_all_parsed_files

BASE_DIRECTORY = Path(__file__).resolve().parent

DATA_DIRECTORY = BASE_DIRECTORY / "data"
RAW_DATA_DIRECTORY = DATA_DIRECTORY / "raw"
PARSED_DATA_DIRECTORY = DATA_DIRECTORY / "parsed"
REVIEW_DATA_DIRECTORY = DATA_DIRECTORY / "review"
OUTPUT_DIRECTORY = DATA_DIRECTORY / "output"
DATABASE_DIRECTORY = DATA_DIRECTORY / "database"
EXTRACTED_DIRECTORY = DATA_DIRECTORY / "extracted"

def create_directories():
    for folder in [DATA_DIRECTORY, RAW_DATA_DIRECTORY, PARSED_DATA_DIRECTORY, REVIEW_DATA_DIRECTORY, OUTPUT_DIRECTORY, DATABASE_DIRECTORY, EXTRACTED_DIRECTORY]:
        folder.mkdir(parents=True, exist_ok=True)

EXTENSIONS = ['.pdf', ".docx", ".xlsx", '.xls', ".csv", ".txt", ".png", ".jpg", ".jpeg"]

if __name__ == "__main__":
    create_directories()

    files_data = prepare_files(RAW_DATA_DIRECTORY, EXTENSIONS)
    pending_files = get_pending_files(files_data)
    parsed_files = parse_all_files(pending_files)
    saved_paths = save_all_parsed_files(parsed_files, PARSED_DATA_DIRECTORY, files_data)

    print("\nTotal files:", len(files_data))
    print("Successfully parsed:", len(parsed_files))
    print("Saved JSON files:", len(saved_paths))

    for path in saved_paths:
        print("Saved:", path)
