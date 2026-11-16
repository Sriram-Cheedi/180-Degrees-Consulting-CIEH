"""Merge approved processed files into the configured master."""
import json
import shutil
import uuid
from src.backend.storage import write_json


def merge_processed(paths, job_id, processed, columns):
    master_path = paths["master"]
    master_path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive lock prevents two application instances from losing each other's updates.
    lock = master_path.with_suffix(".lock")
    lock_handle = lock.open("x")
    try:
        master = json.loads(master_path.read_text(encoding="utf-8")) if master_path.exists() else {"columns": columns, "records": [], "merged_uploads": []}
        if master["columns"] != columns:
            if not set(columns).issubset(master["columns"]):
                raise ValueError("Master columns differ from config; migrate the master before merging")
            shutil.copy2(master_path, master_path.with_name(f"{master_path.stem}.backup-{uuid.uuid4().hex}.json"))
            master["columns"] = columns
            master["records"] = [{column: row.get(column) for column in columns} for row in master["records"]]
        if job_id not in master["merged_uploads"]:
            approved = json.loads(processed.read_text(encoding="utf-8"))
            master["records"].extend({column: row.get(column) for column in columns} for row in approved["records"])
            master["merged_uploads"].append(job_id)
        seen = set()
        unique = []
        for row in master["records"]:
            signature = json.dumps(row, sort_keys=True, ensure_ascii=False)
            if signature not in seen:
                seen.add(signature)
                unique.append(row)
        master["records"] = unique
        write_json(master_path, master)
    finally:
        lock_handle.close()
        lock.unlink()
