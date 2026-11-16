import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml
from src.backend.pipeline import Workflow
from src.ai.configurable_prompt import build_prompt
from src.settings import load_settings


class WorkflowTests(unittest.TestCase):
    def test_duplicate_upload_reuses_job_even_when_renamed(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config = {"files": {"extensions": [".txt"]}, "gemini": {},
                      "json": {"lines_per_chunk": 100}, "master": {"columns": ["count", "notes"], "output_columns": ["count"]},
                      "paths": {"incoming": "incoming", "working": "working", "processed": "processed", "master": "master.json"}}
            path = base / "config.yaml"
            path.write_text(yaml.safe_dump(config))
            source = base / "source.txt"
            source.write_text("Count 5")
            calls = []
            def aligner(*_):
                calls.append(True)
                return [{"count": 5, "notes": "Evidence"}]
            workflow = Workflow(path, aligner)
            job = workflow.process(source, "txt")
            renamed = base / "renamed.txt"
            renamed.write_bytes(source.read_bytes())
            duplicate = workflow.process(renamed, "txt")
            self.assertEqual(duplicate["id"], job["id"])
            self.assertTrue(duplicate["duplicate_upload"])
            self.assertEqual(len(calls), 1)
            workflow.decide(job["id"], True)
            self.assertEqual(workflow.process(renamed, "txt")["status"], "merged")
            self.assertEqual(len(list((base / "working").iterdir())), 1)
            master = json.loads((base / "master.json").read_text())
            self.assertEqual(master["columns"], ["count"])
            self.assertEqual(master["records"], [{"count": 5}])

    def test_corrections_are_saved_and_merged_with_originals_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config = {"files": {"extensions": [".txt"]}, "gemini": {},
                      "json": {"lines_per_chunk": 100}, "master": {"columns": ["category", "count"]},
                      "paths": {"incoming": "incoming", "working": "working", "processed": "processed", "master": "master.json"}}
            path = base / "config.yaml"
            path.write_text(yaml.safe_dump(config))
            source = base / "source.txt"
            source.write_text("Test")
            rows = [{"category": category, "count": 5} for category in ("tattoo_premises", "tattoo_practitioners", "combined_premises_and_practitioners")]
            workflow = Workflow(path, lambda *_: rows)
            job = workflow.process(source, "txt")
            with self.assertRaises(ValueError):
                workflow.save_corrections(job["id"], {"0": {"count": -1}})
            workflow.save_corrections(job["id"], {"0": {"count": 0}, "1": {"count": 12}, "2": {"count": 17}})
            restored = Workflow(path)
            self.assertEqual(restored.pending()[0]["records"][0]["count"], 5)
            restored.decide(job["id"], True)
            master = json.loads((base / "master.json").read_text())
            self.assertEqual([row["count"] for row in master["records"]], [0, 12, 17])
            processed = json.loads((base / "processed" / (job["id"] + ".json")).read_text())
            self.assertEqual([row["count"] for row in processed["original_records"]], [5, 5, 5])
            with self.assertRaises(ValueError):
                restored.save_corrections(job["id"], {})

    def test_retry_saved_upload_after_model_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config = {"files": {"extensions": [".txt"]}, "gemini": {},
                      "json": {"lines_per_chunk": 1}, "master": {"columns": ["count"]},
                      "paths": {"incoming": "incoming", "working": "working", "processed": "processed", "master": "master.json"}}
            config_path = base / "config.yaml"
            config_path.write_text(yaml.safe_dump(config))
            source = base / "source.txt"
            source.write_text("Count 5")
            workflow = Workflow(config_path, lambda *_: (_ for _ in ()).throw(RuntimeError("Model unavailable")))
            with self.assertRaisesRegex(RuntimeError, "Model unavailable"):
                workflow.process(source, "txt")
            failed = workflow.failed()[0]
            source.unlink()  # The original upload/temp file is no longer available.
            with self.assertRaises(RuntimeError):
                workflow.retry(failed["id"])
            self.assertEqual(workflow.failed()[0]["retry_count"], 1)
            workflow = Workflow(config_path, lambda *_: [{"count": 5}])
            with patch("src.parsing.file_parser.parse_file", side_effect=AssertionError("Should reuse parsed source")):
                job = workflow.retry(failed["id"])
            self.assertEqual(job["id"], failed["id"])
            self.assertEqual(job["status"], "pending")
            self.assertEqual(job["retry_count"], 2)
            self.assertNotIn("error", job)
            self.assertEqual(job["records"], [{"count": 5}])
            self.assertEqual(workflow.failed(), [])
            self.assertEqual(len(list((base / "working").iterdir())), 1)
            self.assertFalse((base / "master.json").exists())
            with self.assertRaisesRegex(ValueError, "Only failed"):
                workflow.retry(job["id"])

    def test_full_context_crosses_distant_chunks_and_worksheets(self):
        cases = [
            ("These figures are applications received.\n2023: 5\nSpacer\n2024: 8\nThese are not approvals.",
             "applications received", "not approvals"),
            ({"Guidance": [["These figures are applications received."]],
              "Counts": [["Year", "Count"], ["2023", "5"], ["2024", "8"]],
              "Footnotes": [["These are not approvals."]]},
             "applications received", "not approvals"),
        ]
        for content, earlier, later in cases:
            with self.subTest(content_type=type(content).__name__), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                config = {"files": {"extensions": [".txt"]}, "gemini": {},
                          "json": {"lines_per_chunk": 1, "context_overlap_lines": 1},
                          "master": {"columns": ["metric_type", "count"]},
                          "paths": {"incoming": "incoming", "working": "working", "processed": "processed", "master": "master.json"}}
                config_path = base / "config.yaml"
                config_path.write_text(yaml.safe_dump(config))
                source = base / "source.txt"
                source.write_text("placeholder")
                seen = []
                def aligner(chunk, settings):
                    seen.append(chunk)
                    context = json.dumps(chunk["document_context"])
                    self.assertIn(earlier, context)
                    self.assertIn(later, context)
                    self.assertEqual(chunk["document_context"]["source_id"], chunk["source_id"])
                    prompt = build_prompt(chunk, settings)
                    self.assertIn("ONLY from the target content", prompt)
                    # Simulate extracting only the numeric observations owned by this chunk.
                    return [{"metric_type": "applications", "count": 5}] if "2023" in str(chunk["content"]) else []
                workflow = Workflow(config_path, aligner)
                with patch("src.parsing.file_parser.parse_file", return_value={"content": content}):
                    job = workflow.process(source, "txt")
                self.assertEqual(job["records"], [{"metric_type": "applications", "count": 5}])
                self.assertEqual([chunk["chunk_number"] for chunk in seen], list(range(1, len(seen) + 1)))
                self.assertTrue(all(chunk["total_chunks"] == len(seen) for chunk in seen))
                saved = json.loads((base / "working" / job["id"] / "document.json").read_text())
                self.assertEqual(saved["content"], content)
                if isinstance(content, str):
                    self.assertEqual(seen[1]["previous_context"], ["These figures are applications received."])
                    self.assertEqual(seen[1]["next_context"], ["Spacer"])

    def test_prompt_switches_domain_from_configuration(self):
        config = {"extraction": {"context": "Retail invoice processing", "record_definition": "One row per invoice line",
                                 "rules": ["Preserve currency"]},
                  "master": {"columns": ["product_name", "quantity"], "column_definitions": {
                      "product_name": {"description": "Product sold", "aliases": ["Item"]}}}}
        prompt = build_prompt({"content": "Item: Soap, Qty: 3"}, config)
        for expected in ("Retail invoice processing", "One row per invoice line", "Product sold", "Item", "quantity", "Preserve currency"):
            self.assertIn(expected, prompt)
        self.assertNotIn("tattoo", prompt.lower())
        self.assertNotIn("CIEH", prompt)
        default_prompt = build_prompt({"content": "test"}, load_settings())
        self.assertIn("tattoo", default_prompt)
        self.assertIn("new_registrations", default_prompt)

    def test_custom_columns_flow_through_to_master(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config = {"files": {"extensions": [".txt"]}, "gemini": {},
                      "json": {"lines_per_chunk": 10},
                      "extraction": {"context": "Retail invoices"},
                      "master": {"columns": ["product_name", "quantity", "currency"]},
                      "paths": {"incoming": "incoming", "working": "working", "processed": "processed", "master": "master.json"}}
            config_path = base / "config.yaml"
            config_path.write_text(yaml.safe_dump(config))
            source = base / "invoice.txt"
            source.write_text("Soap: 3")
            workflow = Workflow(config_path, lambda *_: [{"product_name": "Soap", "quantity": 3, "extra": "ignored"}])
            job = workflow.process(source, "txt")
            workflow.config["master"]["columns"] = ["different_column"]
            with self.assertRaisesRegex(ValueError, "Upload columns differ"):
                workflow.decide(job["id"], True)
            workflow.config["master"]["columns"] = ["product_name", "quantity", "currency"]
            workflow.decide(job["id"], True)
            master = json.loads((base / "master.json").read_text())
            self.assertEqual(master["records"], [{"product_name": "Soap", "quantity": 3, "currency": None}])

    def test_review_gate_chunks_and_idempotent_merge(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config = {"files": {"extensions": [".csv"]}, "gemini": {},
                      "json": {"lines_per_chunk": 1}, "master": {"columns": ["year", "count", "missing"]},
                      "paths": {"incoming": "incoming", "working": "working", "processed": "processed", "master": "master/data.json"}}
            config_path = base / "config.yaml"
            config_path.write_text(yaml.safe_dump(config))
            source = base / "sample.csv"
            source.write_text("Year,Count\n2023,0\n2024,5\n")
            chunks = []
            def aligner(chunk, settings):
                chunks.append(chunk)
                return [{"year": chunk["content"][0][0], "count": int(chunk["content"][0][1]), "extra": 99}]
            workflow = Workflow(config_path, aligner)
            # A mistaken selection must not route a CSV to the PDF parser.
            job = workflow.process(source, "pdf")
            master_path = workflow.config["paths"]["master"]
            self.assertFalse(master_path.exists())
            self.assertTrue(source.exists())
            self.assertEqual(len(chunks), 2)
            self.assertEqual(chunks[1]["header"], [["Year", "Count"]])
            self.assertEqual(job["records"][0], {"year": "2023", "count": 0, "missing": None})
            self.assertEqual(len(workflow.pending()), 1)
            workflow.decide(job["id"], True)
            master = json.loads(master_path.read_text())
            self.assertEqual(len(master["records"]), 2)
            with self.assertRaises(ValueError):
                workflow.decide(job["id"], True)
            source.write_text("Year,Count\n2025,9\n")
            discarded = workflow.process(source, "csv")
            workflow.decide(discarded["id"], False)
            self.assertEqual(json.loads(master_path.read_text()), master)
            self.assertEqual(workflow.pending(), [])

    def test_merge_error_releases_lock_and_can_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config = {"files": {"extensions": [".txt"]}, "gemini": {},
                      "json": {"lines_per_chunk": 5}, "master": {"columns": ["count"]},
                      "paths": {"incoming": "incoming", "working": "working", "processed": "processed", "master": "master.json"}}
            config_path = base / "config.yaml"
            config_path.write_text(yaml.safe_dump(config))
            source = base / "sample.txt"
            source.write_text("Count 5")
            workflow = Workflow(config_path, lambda *_: [{"count": 5}])
            job = workflow.process(source, "txt")
            master_path = base / "master.json"
            master_path.write_text("invalid json")
            with self.assertRaises(ValueError):
                workflow.decide(job["id"], True)
            self.assertFalse((base / "master.lock").exists())
            master_path.write_text(json.dumps({"columns": ["count"], "records": [], "merged_uploads": []}))
            workflow.decide(job["id"], True)
            self.assertEqual(len(json.loads(master_path.read_text())["records"]), 1)


if __name__ == "__main__":
    unittest.main()
