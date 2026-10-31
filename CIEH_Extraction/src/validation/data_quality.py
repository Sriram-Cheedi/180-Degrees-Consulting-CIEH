
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from src.ai.extraction_schema import ExtractionRecord


def valid_year(year: str | None) -> bool:
    if year is None:
        return False

    year = str(year).strip()
    current_year = datetime.now().year

    # Calendar year: 2023
    if re.fullmatch(r"\d{4}", year):
        return 1900 <= int(year) <= current_year

    # Financial year: 2023/24 or 2023-24
    match = re.fullmatch(r"(\d{4})[/-](\d{2}|\d{4})", year)

    if match:
        start = int(match.group(1))
        ending = match.group(2)

        end = (
            int(ending)
            if len(ending) == 4
            else (start // 100) * 100 + int(ending)
        )

        return (
            1900 <= start <= current_year
            and end == start + 1
        )

    return False


def audit_extractions(extracted_directory: Path):
    extracted_directory = Path(extracted_directory)

    issues = []
    total_records = 0
    seen_sources = set()
    observations = defaultdict(list)

    def flag(record_id, filename, issue_type, message):
        issues.append({
            "record_id": record_id,
            "filename": filename,
            "issue_type": issue_type,
            "message": message
        })

    for json_path in sorted(extracted_directory.glob("*.json")):

        data = json.loads(
            json_path.read_text(encoding="utf-8")
        )

        source = data.get("source") or {}
        file_hash = source.get("file_hash")

        if not file_hash:
            raise ValueError(
                f"Missing file hash: {json_path.name}"
            )

        if file_hash in seen_sources:
            continue

        seen_sources.add(file_hash)

        extraction = data.get("extraction") or {}
        filename = data.get("filename") or json_path.name
        council = extraction.get("council_name")
        records = extraction.get("records") or []

        for index, record in enumerate(records, start=1):
            total_records += 1

            record_id = f"{file_hash}-{index:04d}"

            # 1. Council identification
            if not council or not str(council).strip():
                flag(
                    record_id, filename,
                    "missing_council",
                    "Council name not identified"
                )

            # 2. Year validation
            if not valid_year(record.get("year")):
                flag(
                    record_id, filename,
                    "review_year",
                    f"Check year: {record.get('year')}"
                )

            # 3. Schema validation
            try:
                ExtractionRecord.model_validate(record)
            except Exception as error:
                flag(
                    record_id, filename,
                    "schema_error",
                    str(error)
                )

            # 4. Ambiguous category
            if record.get("category") in {"other", "unknown"}:
                flag(
                    record_id, filename,
                    "ambiguous_category",
                    f"Category: {record.get('category')}"
                )

            # 5. Ambiguous metric
            if record.get("metric_type") in {"other", "unknown"}:
                flag(
                    record_id, filename,
                    "ambiguous_metric",
                    f"Metric: {record.get('metric_type')}"
                )

            # 6. Missing supporting evidence
            evidence = record.get("evidence_text")

            if not evidence or not str(evidence).strip():
                flag(
                    record_id, filename,
                    "missing_evidence",
                    "Supporting evidence is missing"
                )

            # 7. Possible duplicate observations
            # Restrict to the same source document.
            key = (
                file_hash,
                record.get("year"),
                record.get("category"),
                record.get("metric_type"),
                record.get("count")
            )

            observations[key].append((record_id, filename))

    for matching_records in observations.values():
        if len(matching_records) > 1:
            ids = [item[0] for item in matching_records]

            for record_id, filename in matching_records:
                flag(
                    record_id, filename,
                    "possible_duplicate",
                    f"Potential duplicate IDs: {', '.join(ids)}"
                )

    summary = {
        "documents_checked": len(seen_sources),
        "records_checked": total_records,
        "issues_found": len(issues),
        "records_flagged": len({
            issue["record_id"] for issue in issues
        })
    }

    return summary, issues