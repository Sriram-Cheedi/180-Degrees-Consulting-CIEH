import pandas as pd
from pathlib import Path

def read_csv_file(file_path):
    file_path = Path(file_path)
    df = pd.read_csv(file_path, header = None, dtype = str, keep_default_na = False)
    return df.values.tolist()


def read_excel_file(file_path):
    file_path = Path(file_path)
    sheets = pd.read_excel(file_path, sheet_name = None, header = None, dtype = str, keep_default_na = False)
    sheets_data = {}

    for sheet_name, df in sheets.items():
        sheets_data[sheet_name] = df.values.tolist()

    return sheets_data


def parse_spreadsheet(file_metadata):
    file_path = file_metadata.get("file_path")
    extension = file_metadata.get("extension")

    if extension == ".csv":
        content = {
            read_csv_file(file_path)
        }
    elif extension in [".xlsx", ".xls"]:
        content = read_excel_file(file_path)
    else:
        raise ValueError(f"Unsupported spreadsheet format: {extension}")

    parsed_data = {
        "source_id": file_metadata.get("source_id"),
        "response_id": file_metadata.get("response_id"),
        "filename": file_metadata.get("filename"),
        "file_type": extension,
        "content": content,
        "parser": "pandas",
        "status": "parsed"
    }

    return parsed_data
    