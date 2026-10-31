# CIEH Extraction Pipeline — Setup & Running Guide

This guide explains how to set up and run the CIEH FOI data extraction pipeline on a Windows computer using VS Code and PowerShell.

The pipeline uses Python to process council FOI responses, Gemini AI to extract structured records, and Excel for human verification.

## 1. Prerequisites

Install the following software:

- **Python 3.12** — https://www.python.org/downloads/
- **Git** — https://git-scm.com/downloads
- **VS Code** — https://code.visualstudio.com/

Make sure Python and Git are accessible from your terminal.

Verify the installations:

```powershell
py -3.12 --version
git --version
```

## 2. Clone the GitHub repository

Open VS Code, then open a PowerShell terminal.

```powershell
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
```

Replace the URL with the actual GitHub repository URL.

Navigate to the Python project folder:

```powershell
cd YOUR-REPOSITORY
cd CIEH_Extraction
```

All subsequent commands should be run from `CIEH_Extraction`, where `main.py` and `requirements.txt` are located.

## 3. Create and activate a virtual environment

Create a Python 3.12 environment:

```powershell
py -3.12 -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

The terminal should now display `(.venv)`.

If PowerShell blocks activation, you can temporarily allow scripts for the current terminal session:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\.venv\Scripts\Activate.ps1
```

## 4. Install project dependencies

Run:

```powershell
python -m pip install -r requirements.txt
```

This installs the required Python libraries, such as Docling, OCR dependencies, Pydantic, pandas, openpyxl and the Gemini SDK, provided they are listed in `requirements.txt`.

Verify that the Gemini SDK works:

```powershell
python -c "from google import genai; print('Gemini SDK working')"
```

If you receive `ImportError: cannot import name 'genai' from 'google'`, install the correct package:

```powershell
python -m pip install google-genai
```

## 5. Configure the Gemini API key

The pipeline requires a Google Gemini API key.

1. Visit https://aistudio.google.com/apikey
2. Create or obtain an API key.
3. Create a file called `.env` inside `CIEH_Extraction`.
4. Add the API key:

```dotenv
GEMINI_API_KEY=YOUR_ACTUAL_API_KEY
```

The variable name must match the project's Gemini client configuration.

**Security:** Never upload `.env` or your API key to GitHub.

Be aware that Gemini usage limits may apply. The model can sometimes return temporary `503 UNAVAILABLE` errors when demand is high.

## 6. Prepare the project folders

The relevant project structure is:

```text
180-Degrees-Consulting-CIEH/
├── .gitignore
├── README.md
└── CIEH_Extraction/
    ├── .env
    ├── .venv/
    ├── requirements.txt
    ├── main.py
    ├── finalize.py
    ├── parse_pipeline.py
    ├── src/
    └── data/
        ├── raw/
        ├── parsed/
        ├── extracted/
        ├── review/
        └── output/
```

If the data folders do not exist, create them from inside `CIEH_Extraction`:

```powershell
New-Item -ItemType Directory -Force data/raw, data/parsed, data/extracted, data/review, data/output
```

## 7. Add council FOI documents

Place original council responses inside:

`CIEH_Extraction/data/raw/`

Supported input formats include:

- PDF (`.pdf`)
- Excel (`.xlsx`, `.xls`)
- Word (`.docx`)
- CSV (`.csv`)
- Text (`.txt`)
- Images (`.png`, `.jpg`, `.jpeg`)

For example:

```text
data/
└── raw/
    ├── Council_A.pdf
    ├── Council_B.xlsx
    ├── Council_C.txt
    └── Council_D.docx
```

Files can be placed directly inside `data/raw/`. Separate council folders are not required.

Do not rename or modify the original responses unnecessarily.

## 8. Run the extraction pipeline

Make sure the virtual environment is active and the terminal is inside `CIEH_Extraction`.

Run:

```powershell
python main.py
```

The pipeline runs four stages:

**Stage 1 — Document parsing**

Discovers and parses source documents into structured JSON, saved to `data/parsed/`.

**Stage 2 — Gemini extraction**

Sends parsed documents to Gemini and saves the structured extraction records in `data/extracted/`.

Previously successful extractions are skipped when the corresponding output exists.

**Stage 3 — Data-quality checks**

Runs automated checks and generates:

`data/review/data_quality_issues.csv`

This identifies records that may need additional attention, such as missing council names or ambiguous metrics.

**Stage 4 — Excel review synchronisation**

Creates or updates:

`data/review/cieh_review.xlsx`

Existing review records are retained, and new records are appended.

A successful run ends with:

```text
=== PIPELINE FINISHED ===
```

Note: Successful processing does not guarantee that AI-extracted values are factually correct. Human verification remains essential.

## 9. Review the extracted data

Open:

`data/review/cieh_review.xlsx`

For every record being reviewed, compare its values against the original council response.

The workbook contains original extraction columns and separate editable review columns.

Set **Review Decision** to one of:

| Decision | Meaning |
|---|---|
| `approved` | AI-extracted values have been verified and are correct |
| `corrected` | One or more extracted values require correction |
| `rejected` | Record should not be included in the final dataset |
| Blank | Not yet reviewed |

For `approved` or `corrected` records, enter the reviewer's name.

For corrections, enter the revised value in the appropriate `Corrected` column rather than overwriting the original extraction.

For example:

| Field | Value |
|---|---|
| Count | 18 |
| Review Decision | corrected |
| Corrected Count | 16 |
| Reviewer | Reviewer name |
| Reviewer Notes | Corrected against the council response |

The final exporter uses `16`, while the original extracted value remains available for comparison.

Save and close Excel before running the next stage.

## 10. Export the verified dataset

Run:

```powershell
python finalize.py
```

This reads the review workbook, applies approved corrections, validates the resulting records and generates:

```text
data/output/
├── cieh_verified.csv
└── cieh_verified.xlsx
```

Only approved and corrected records are included. Pending and rejected records are excluded.

If an approved or corrected row has no reviewer name, the exporter will raise an error specifying the Excel row that needs attention.

After a successful export, open `cieh_verified.xlsx` and verify that the expected records and corrected values are present.

## 11. Adding new council responses later

To process more FOI responses:

1. Copy the new files into `data/raw/`.
2. Run `python main.py` again.
3. Open `data/review/cieh_review.xlsx`.
4. Review the newly added records.
5. Run `python finalize.py` to regenerate the verified outputs.

Previously extracted documents are skipped during the Gemini extraction stage, based on their existing extraction files.

Existing human review decisions are designed to be preserved during review-sheet synchronisation.

Avoid deleting `data/extracted/` or overwriting the master review workbook without a backup.

## 12. Common troubleshooting

**Error: `No module named ...`**

Activate `.venv` and reinstall the dependencies:

```powershell
python -m pip install -r requirements.txt
```

**Error: `cannot import name 'genai' from 'google'`**

```powershell
python -m pip install google-genai
```

**Error: Gemini API key missing**

Check that `.env` exists, the key is correctly named, and the application loads environment variables.

**Error: `503 UNAVAILABLE`**

Gemini may be temporarily overloaded. Retry later using:

```powershell
python main.py
```

Previously completed extraction files should be skipped.

**Error: `Reviewer is required`**

Open `data/review/cieh_review.xlsx`, locate the reported row and enter a reviewer name for the approved or corrected record.

**Error: `PermissionError` involving Excel**

Close the review or output workbook in Excel, then rerun the command.
