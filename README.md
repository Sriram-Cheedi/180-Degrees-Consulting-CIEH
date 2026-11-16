# 180-Degrees-Consulting-CIEH

Run the architecture-diagram workflow from the repository root:

```powershell
.venv\Scripts\python.exe -m streamlit run CIEH_Extraction\app.py
```

Choose the file format, upload a file, inspect the extracted table, then select
**Accept and merge** or **Discard**. Gemini calls require `GEMINI_API_KEY` in
`CIEH_Extraction/.env`. The configured model must be available to your API account.
The app uses the existing pandas, Docling and OCR parsers; these dependencies
must be installed in the Python environment.

`CIEH_Extraction/config.yaml` controls supported formats, Gemini settings, incoming,
working and processed directories, the master JSON path, master column names and
`json.lines_per_chunk`. Relative paths resolve from the config file's directory.
Chunks contain at most that many text lines or spreadsheet data rows; spreadsheet
headers and sheet names are retained as context in every chunk. Keep related
observations together by increasing the chunk size when needed.

Every extraction request also receives the **entire parsed document**, including
all worksheets, plus nearby lines/rows controlled by `json.context_overlap_lines`.
This lets a table use explanations before or after it, even across chunk or sheet
boundaries. `working/<upload UUID>/document.json` preserves that shared source;
each chunk retains its source ID, position and total chunk count. The prompt limits
extraction to the target chunk's observations so contextual data is not extracted
again. Meaning must still be scoped to the appropriate table or section.

Full-document context increases API input usage, and large documents can exceed
the model's input limit. Such requests fail visibly rather than silently dropping
context. This does not guarantee correct model interpretation; preview remains
required. Previously extracted uploads need reprocessing to use this behavior.

Uploads are copied into incoming with a UUID, moved into working, parsed to JSON
chunks and read back for LLM column matching. Only configured columns survive;
missing values become JSON null. Review is mandatory before merging. Acceptance
saves a processed JSON file and merges its records into the master JSON. Upload
IDs prevent the same accepted upload from being merged twice. Identical file contents reuse the existing upload even if the file is renamed; no extra extraction or copy is created. Identical master observations are stored once.
Discarded and failed uploads remain in working for audit; original files are preserved.
Pending reviews resume when the app starts. Master schema changes require an
explicit migration of any existing master. A master lock blocks simultaneous merges;
after a forced process termination, remove a stale `.lock` only after confirming
no other merge is running.

The original batch/Excel workflow remains available through `main.py` and `finalize.py`.

The code and data folders follow the architecture:

```text
CIEH_Extraction/
  app.py                    # launch the frontend
  config.yaml               # paths, columns, chunk size, LLM settings
  src/
    frontend/streamlit_app.py # upload, preview, accept/discard
    backend/pipeline.py      # stage uploads and coordinate processing
    backend/storage.py       # atomic JSON writes
    ingestion/               # existing batch file discovery and metadata
    parsing/                 # CSV, Excel, document and OCR parsing
    ai/                      # existing CIEH extraction tools
    review/                  # existing Excel review tools
    validation/              # existing quality checks
    merge/master.py          # approved processed data -> master
    settings.py              # load and validate configuration
  data/
    incoming/                # temporary UUID uploads
    working/<upload UUID>/   # source, JSON chunks and review status
    processed/               # accepted upload JSON
    master/                  # merged master JSON
  tests/test_workflow.py     # workflow checks without API calls
```

Existing `raw`, `parsed`, `extracted`, `review`, `output` and `database` data
folders belong to the batch workflow and remain in place. They are not automatically
migrated into approved data. `src/workflow.py` and `test_workflow.py` retain
compatibility imports for the new module locations.

Local workflow checks (no API calls):

```powershell
cd CIEH_Extraction
..\.venv\Scripts\python.exe -m unittest test_workflow
```

### Using another industry or dataset

The Streamlit workflow builds its extraction prompt from configuration. The default
configuration retains the tattoo FOI guidance. To change datasets, edit
`extraction.context`, `extraction.record_definition`, `extraction.rules`, and
`master.columns`. Optionally describe each field in `master.column_definitions`,
including source aliases and allowed values. These definitions guide the LLM;
they do not enforce value types or enum validation in Python.

For example, replace the extraction and master sections for retail invoices:

```yaml
extraction:
  context: Retail purchase invoices
  record_definition: One record per invoice line item
  rules:
    - Preserve the currency explicitly stated in the invoice.
master:
  columns: [invoice_number, product_name, quantity, unit_price, currency]
  column_definitions:
    quantity:
      description: Number of units purchased on this invoice line.
      aliases: [Qty, Units]
    unit_price:
      description: Price per unit, not the line total; null if absent.
      aliases: [Unit Cost, Price Each]
```

Prefer meaningful names and define ambiguous fields. Column names alone work
with generic instructions if the `extraction` section is omitted, but they cannot
reliably convey a dataset's business meaning. Remove outdated column definitions
when replacing columns. Use separate incoming, working, processed and master paths
for a different dataset, then restart the app to load the edited configuration.
An existing master with different columns is rejected rather than automatically
migrated. Uploads retain their extraction specification for audit and cannot be
accepted under different columns. This configurable behavior applies to `app.py`;
the legacy batch/Excel workflow remains specific to the CIEH schema.

The default interface is Streamlit with Upload, Review and Master data tabs.
Review includes a category dropdown for tattoo premises, practitioners and both
combined (plus all records and any other extracted categories). Select a column
to correct; count is selected by default. Original fields are read-only, with a
separate corrected-value column. Blank corrections leave the original unchanged;
zero is a valid corrected count. Edits carry across category filters. Use
**Save changes made** before leaving the upload to persist drafts across restarts.
**Changes made — accept and merge**, or **Accept and merge**, applies all corrections
across the upload before merging. Original records and corrections remain in the
processed JSON for audit. Corrections cannot modify an already accepted upload.
Only the current failed upload shows **Retry extraction**; historical failures are not
listed. Retry uses the saved source and current settings without another upload.
Selecting a new upload clears the previous retry control. Reuploading an identical
failed file retrieves that failed job rather than creating another copy.

`master.output_columns` controls the final master independently of extraction and
review columns. The tattoo master contains only council_name, year, category,
metric_type and count. Evidence and notes remain in working/processed review data.
Reducing master output columns creates a backup before projecting existing records;
identical projected observations are stored once. File matching is byte-for-byte;
a differently exported or edited copy may have a different hash.

Install its dependency with `.venv\Scripts\python.exe -m pip install streamlit`.
The earlier Tkinter frontend remains available as `python -m src.frontend.app`
from the `CIEH_Extraction` directory.
