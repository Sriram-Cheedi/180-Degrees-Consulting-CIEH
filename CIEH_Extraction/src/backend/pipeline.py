"""Upload -> working JSON -> LLM alignment -> human review -> master merge."""
import json
import hashlib
import os
import shutil
import uuid
from pathlib import Path

from src.settings import BASE_DIR, load_settings
from src.ai.configurable_prompt import build_prompt


from src.backend.storage import write_json


def align_columns(document, config):
    from dotenv import load_dotenv
    from google import genai
    from google.genai import types
    load_dotenv(BASE_DIR / ".env")
    settings = config["gemini"]
    key = settings.get("api_key") or os.getenv(settings.get("api_key_env", "GEMINI_API_KEY"))
    if not key:
        raise ValueError("Configure the Gemini API key in .env")
    columns = config["master"]["columns"]
    prompt = build_prompt(document, config)
    with genai.Client(api_key=key) as client:
        response = client.models.generate_content(
            model=settings["model"], contents=prompt,
            config=types.GenerateContentConfig(temperature=settings.get("temperature", 0),
                                               response_mime_type="application/json"),
        )
    result = json.loads(response.text or "{}")
    rows = result.get("records")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("LLM must return a records array of objects")
    return [{column: row.get(column) for column in columns} for row in rows]


class Workflow:
    def __init__(self, config_path=None, aligner=None):
        self.config = load_settings(config_path)
        self.aligner = aligner or align_columns
        self.current_job_id = None

    def process(self, source, declared_format=None):
        source = Path(source)
        extension = source.suffix.lower()
        # Keep the optional argument for older callers; the filename determines
        # the parser, regardless of a mistaken manual selection.
        if extension not in self.config["files"]["extensions"]:
            raise ValueError(f"Unsupported file extension: {extension or '(missing)'}")
        if not source.is_file() or source.stat().st_size == 0:
            raise ValueError("Upload a nonempty file")
        file_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        matches = []
        for path in self.config["paths"]["working"].glob("*/job.json"):
            previous = json.loads(path.read_text(encoding="utf-8"))
            previous_hash = previous.get("file_hash")
            if not previous_hash:
                saved = path.parent / (previous["id"] + Path(previous["filename"]).suffix.lower())
                if saved.is_file():
                    previous_hash = hashlib.sha256(saved.read_bytes()).hexdigest()
            if previous_hash == file_hash:
                matches.append(previous)
        if matches:
            previous = min(matches, key=lambda job: {"merged": 0, "accepted": 1, "pending": 2, "failed": 3}.get(job["status"], 4))
            self.current_job_id = previous["id"]
            return {**previous, "duplicate_upload": True}
        job_id = str(uuid.uuid4())
        self.current_job_id = job_id
        paths = self.config["paths"]
        incoming = paths["incoming"] / (job_id + extension)
        working = paths["working"] / job_id
        incoming.parent.mkdir(parents=True, exist_ok=True)
        working.mkdir(parents=True)
        shutil.copy2(source, incoming)
        staged = Path(shutil.move(str(incoming), str(working / incoming.name)))
        manifest = {"id": job_id, "filename": source.name, "status": "processing", "file_hash": file_hash,
                    "columns": self.config["master"]["columns"],
                    "extraction_spec": self.config.get("extraction", {}),
                    "column_definitions": self.config["master"].get("column_definitions", {})}
        write_json(working / "job.json", manifest)
        return self._run(staged, working, manifest)

    def failed(self):
        jobs = []
        for path in self.config["paths"]["working"].glob("*/job.json"):
            job = json.loads(path.read_text(encoding="utf-8"))
            if job["status"] == "failed":
                jobs.append(job)
        return jobs

    def retry(self, job_id):
        job_id = str(uuid.UUID(job_id))
        working = self.config["paths"]["working"] / job_id
        job = json.loads((working / "job.json").read_text(encoding="utf-8"))
        if job["status"] != "failed":
            raise ValueError("Only failed uploads can be retried")
        extension = Path(job["filename"]).suffix.lower()
        staged = working / (job_id + extension)
        if not staged.is_file():
            raise FileNotFoundError("Saved source is missing; upload the original file again")
        if extension not in self.config["files"]["extensions"]:
            raise ValueError("Saved source format is no longer enabled in config")
        job.update(status="processing", columns=self.config["master"]["columns"],
                   extraction_spec=self.config.get("extraction", {}),
                   column_definitions=self.config["master"].get("column_definitions", {}),
                   retry_count=job.get("retry_count", 0) + 1)
        job.pop("error", None)
        job.pop("records", None)
        write_json(working / "job.json", job)
        return self._run(staged, working, job)

    def _run(self, staged, working, manifest):
        from src.parsing.file_parser import parse_file
        job_id = manifest["id"]
        source = Path(manifest["filename"])
        extension = staged.suffix.lower()
        try:
            saved_document = working / "document.json"
            if saved_document.exists():
                content = json.loads(saved_document.read_text(encoding="utf-8"))["content"]
            else:
                parsed = parse_file({"file_path": str(staged), "filename": source.name,
                                     "extension": extension, "source_id": job_id})
                content = parsed["content"]
            # Keep the full parsed source, including other worksheets and trailing
            # explanations. Chunk boundaries must never hide document context.
            document_context = {"source_id": job_id, "filename": source.name,
                                "content": content}
            write_json(working / "document.json", document_context)
            # Text chunks contain lines; spreadsheet chunks contain rows, retaining sheet/header context.
            if isinstance(content, str):
                groups = [(None, content.splitlines(), None)]
            elif isinstance(content, list):
                groups = [(None, content[1:], content[:1])]
            elif isinstance(content, dict):
                groups = [(name, rows[1:], rows[:1]) for name, rows in content.items()]
            else:
                raise ValueError("Unsupported parser content")
            size = self.config["json"]["lines_per_chunk"]
            overlap = self.config["json"].get("context_overlap_lines", 5)
            total_chunks = sum((len(lines) + size - 1) // size for _, lines, _ in groups)
            records = []
            chunk_number = 0
            for sheet, lines, header in groups:
                for offset in range(0, len(lines), size):
                    chunk_number += 1
                    chunk = {"source_id": job_id, "filename": source.name, "sheet": sheet,
                             "header": header, "start_line": offset + 1,
                             "end_line": min(offset + size, len(lines)),
                             "chunk_number": chunk_number, "total_chunks": total_chunks,
                             "previous_context": lines[max(0, offset - overlap):offset],
                             "next_context": lines[offset + size:offset + size + overlap],
                             "content": lines[offset:offset + size]}
                    chunk_path = working / f"chunk_{chunk_number:05}.json"
                    write_json(chunk_path, chunk)
                    extraction_input = json.loads(chunk_path.read_text(encoding="utf-8"))
                    extraction_input["document_context"] = document_context
                    rows = self.aligner(extraction_input, self.config)
                    columns = self.config["master"]["columns"]
                    records.extend({column: row.get(column) for column in columns} for row in rows)
            if not records:
                raise ValueError("No records extracted; nothing to review")
            manifest.update(status="pending", records=records)
        except Exception as error:
            manifest.update(status="failed", error=str(error))
            write_json(working / "job.json", manifest)
            raise
        write_json(working / "job.json", manifest)
        return manifest

    def pending(self):
        jobs = []
        for path in self.config["paths"]["working"].glob("*/job.json"):
            job = json.loads(path.read_text(encoding="utf-8"))
            if job["status"] in {"pending", "accepted"}:
                jobs.append(job)
        return jobs

    def save_corrections(self, job_id, corrections):
        """Persist reviewed values separately from the original extraction."""
        job_id = str(uuid.UUID(job_id))
        path = self.config["paths"]["working"] / job_id / "job.json"
        job = json.loads(path.read_text(encoding="utf-8"))
        if job["status"] != "pending":
            raise ValueError("Only pending uploads can be edited")
        columns = job.get("columns", list(job["records"][0]))
        validated = {}
        for row_id, fields in corrections.items():
            index = int(row_id)
            if index < 0 or index >= len(job["records"]) or not isinstance(fields, dict):
                raise ValueError("Invalid correction row")
            validated[str(index)] = {}
            for column, value in fields.items():
                if column not in columns:
                    raise ValueError(f"Unknown correction column: {column}")
                if column == "count" and value is not None:
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or int(value) != value:
                        raise ValueError("Corrected count must be a nonnegative integer")
                    value = int(value)
                validated[str(index)][column] = value
        job["corrections"] = validated
        write_json(path, job)
        return job

    def decide(self, job_id, accept):
        job_id = str(uuid.UUID(job_id))
        paths = self.config["paths"]
        job_path = paths["working"] / job_id / "job.json"
        job = json.loads(job_path.read_text(encoding="utf-8"))
        if job["status"] not in {"pending", "accepted"}:
            raise ValueError("This upload has already been reviewed")
        if accept and job.get("columns", list(job["records"][0])) != self.config["master"]["columns"]:
            raise ValueError("Upload columns differ from current config. Restore its config or reprocess the source.")
        if not accept:
            if job["status"] == "accepted":
                raise ValueError("An accepted upload cannot be discarded")
            job["status"] = "discarded"
            write_json(job_path, job)
            return job
        # Persist acceptance before merging so an interrupted merge can be resumed.
        if job["status"] == "pending":
            job.setdefault("original_records", job["records"])
            job["records"] = [dict(row) for row in job["original_records"]]
            for index, fields in job.get("corrections", {}).items():
                job["records"][int(index)].update(fields)
        job["status"] = "accepted"
        write_json(job_path, job)
        processed = paths["processed"] / f"{job_id}.json"
        write_json(processed, job)
        from src.merge.master import merge_processed
        merge_processed(paths, job_id, processed, self.config["master"].get("output_columns", self.config["master"]["columns"]))
        job["status"] = "merged"
        write_json(job_path, job)
        return job
