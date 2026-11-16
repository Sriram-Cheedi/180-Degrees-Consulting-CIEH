"""Streamlit frontend for the configurable extraction workflow."""
import json
from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

from src.backend.pipeline import Workflow
from src.frontend.review_editor import review_editor
from src.review.master_excel import build_master_excel


def main():
    st.set_page_config(page_title="CIEH Extraction", layout="wide")
    st.title("Document extraction and review")
    try:
        workflow = Workflow()
    except Exception as error:
        st.error(f"Could not load config.yaml: {error}")
        return
    columns = workflow.config["master"]["columns"]
    with st.sidebar:
        st.header("Extraction settings")
        st.write(workflow.config.get("extraction", {}).get("context", "Configurable document extraction"))
        st.caption("Output columns")
        output_columns = workflow.config["master"].get("output_columns", columns)
        definitions = workflow.config["master"].get("column_definitions", {})
        for column in output_columns:
            definition = definitions.get(column, {})
            st.markdown(f"**{column}**")
            st.caption(definition.get("description", "No description configured for this column."))
            if definition.get("allowed_values"):
                st.caption("Possible values: " + ", ".join(str(value) for value in definition["allowed_values"]))
        review_columns = [column for column in columns if column not in output_columns]
        if review_columns:
            with st.expander("Additional review fields"):
                st.caption("These support review and are not included in the final master output.")
                for column in review_columns:
                    st.markdown(f"**{column}**")
                    st.caption(definitions.get(column, {}).get("description", "No description configured for this column."))
        st.caption("Settings are loaded from config.yaml. Refresh after editing.")
    if "workflow_notice" in st.session_state:
        st.success(st.session_state.pop("workflow_notice"))
    upload_tab, review_tab, master_tab = st.tabs(["Upload", "Review", "Master data"])
    with upload_tab:
        with st.form("upload_form"):
            uploaded = st.file_uploader("Choose a document", type=[ext.lstrip(".") for ext in workflow.config["files"]["extensions"]])
            declared = st.selectbox("File format", workflow.config["files"]["extensions"])
            st.caption("If the selected format differs from the filename extension, the detected extension is used automatically.")
            submitted = st.form_submit_button("Process document")
        st.caption("Processing sends document content to Gemini. Review is required before merging.")
        if submitted:
            st.session_state.pop("current_failed_job", None)
            if uploaded is None:
                st.warning("Choose a file first.")
            else:
                try:
                    with st.spinner("Parsing and extracting with shared document context…"):
                        with tempfile.TemporaryDirectory() as temporary:
                            source = Path(temporary) / Path(uploaded.name.replace("\\", "/")).name
                            source.write_bytes(uploaded.getvalue())
                            st.caption(f"Detected file type: {source.suffix.lower()}")
                            if declared != source.suffix.lower():
                                st.info(f"Selected format: {declared}. Using the detected format {source.suffix.lower()} instead.")
                            job = workflow.process(source, declared)
                    st.session_state["selected_job"] = job["id"]
                    if job["status"] == "failed":
                        st.session_state["current_failed_job"] = job["id"]
                        st.error(job.get("error", "Processing failed"))
                    elif job.get("duplicate_upload"):
                        st.info(f"This file already exists ({job['status']}). No copy or extra extraction was created.")
                    else:
                        st.success("Extraction ready. Open the Review tab to inspect it.")
                except Exception as error:
                    st.error(f"Processing failed: {error}")
                    if workflow.current_job_id:
                        st.session_state["current_failed_job"] = workflow.current_job_id
        failed_id = st.session_state.get("current_failed_job")
        if failed_id:
            st.caption("Retry the current upload using its saved file and current settings.")
            if st.button("Retry extraction", key="retry_failed"):
                try:
                    with st.spinner("Retrying the saved document?"):
                        job = workflow.retry(failed_id)
                    st.session_state.pop("current_failed_job", None)
                    st.session_state["selected_job"] = job["id"]
                    st.session_state["workflow_notice"] = "Retry succeeded. Open Review to inspect the result."
                    st.rerun()
                except Exception as error:
                    st.error(f"Retry failed: {error}")
    with review_tab:
        jobs = workflow.pending()
        if not jobs:
            st.info("No uploads awaiting review.")
        else:
            by_id = {job["id"]: job for job in jobs}
            identifiers = list(by_id)
            selected = st.selectbox("Upload to review", identifiers,
                                    index=identifiers.index(st.session_state.get("selected_job")) if st.session_state.get("selected_job") in identifiers else 0,
                                    format_func=lambda value: f"{by_id[value]['filename']} — {value}")
            job = by_id[selected]
            job_columns = job.get("columns", list(job["records"][0]))
            corrections = review_editor(job, job_columns, disabled=job["status"] != "pending")
            st.caption(f"{len(job['records'])} records · Status: {job['status']}")
            changed = job_columns != columns
            if changed:
                st.warning("These columns differ from current config. Restore the upload's config or discard and reprocess it.")
            if st.button("Save changes made", disabled=changed or job["status"] != "pending"):
                try:
                    workflow.save_corrections(selected, corrections)
                    st.success("Corrections saved. Accept and merge when all categories are reviewed.")
                except Exception as error:
                    st.error(f"Could not save corrections: {error}")
            accept, corrected, discard = st.columns(3)
            decision = None
            if accept.button("Accept and merge", disabled=changed, type="primary"):
                decision = True
            if corrected.button("Changes made — accept and merge", disabled=changed or job["status"] != "pending"):
                decision = True
            if discard.button("Discard", disabled=job["status"] == "accepted"):
                decision = False
            if decision is not None:
                try:
                    if decision and job["status"] == "pending":
                        workflow.save_corrections(selected, corrections)
                    workflow.decide(selected, decision)
                    st.session_state["workflow_notice"] = "Accepted and merged into master." if decision else "Discarded. Master data is unchanged."
                    st.rerun()
                except Exception as error:
                    st.error(f"Review failed: {error}")
    with master_tab:
        path = workflow.config["paths"]["master"]
        if not path.exists():
            st.info("Master data will appear after the first accepted upload.")
        else:
            try:
                master = json.loads(path.read_text(encoding="utf-8"))
                frame = pd.DataFrame(master["records"], columns=master["columns"])
                st.dataframe(frame, hide_index=True, width="stretch")
                st.download_button("Download master JSON", json.dumps(master, ensure_ascii=False, indent=2), "master.json", "application/json")
                st.download_button("Download master CSV", frame.to_csv(index=False).encode("utf-8-sig"), "master.csv", "text/csv")
                st.download_button("Download formatted Excel", build_master_excel(master), "master.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                st.caption("Excel includes fitted column widths, wrapped text, filters and a frozen header. CSV contains plain data only.")
            except Exception as error:
                st.error(f"Could not read master: {error}")
