"""Category-filtered review with separate original and corrected values."""
import pandas as pd
import streamlit as st


def review_editor(job, columns, disabled=False):
    key = f"corrections_{job['id']}"
    if key not in st.session_state:
        st.session_state[key] = {index: dict(fields) for index, fields in job.get("corrections", {}).items()}
    drafts = st.session_state[key]
    categories = ["All records"]
    labels = {"tattoo_premises": "Tattoo premises", "tattoo_practitioners": "Tattoo practitioners",
              "combined_premises_and_practitioners": "Both combined"}
    if "category" in columns:
        categories.extend(labels)
        categories.extend(sorted({row.get("category") for row in job["records"] if row.get("category") and row.get("category") not in labels}))
    category = st.selectbox("Category to review", categories, format_func=lambda value: labels.get(value, value), key=f"category_{job['id']}")
    field = st.selectbox("Column to correct", columns, index=columns.index("count") if "count" in columns else 0, key=f"field_{job['id']}")
    indices = [i for i, row in enumerate(job["records"]) if category == "All records" or row.get("category") == category]
    st.caption("Original values stay visible. Enter corrections separately. Edits carry across categories; save before leaving this upload.")
    if not indices:
        st.info("No records in this category.")
        return drafts
    display = []
    for index in indices:
        row = {"Record": index + 1, **job["records"][index]}
        value = drafts.get(str(index), {}).get(field)
        row["Corrected value"] = value if field == "count" or value is None else str(value)
        display.append(row)
    frame = pd.DataFrame(display)
    configuration = {"Corrected value": st.column_config.NumberColumn("Corrected count", min_value=0, step=1) if field == "count" else st.column_config.TextColumn(f"Corrected {field}")}
    if field == "count":
        frame["Corrected value"] = pd.array(frame["Corrected value"], dtype="Float64")
    else:
        frame["Corrected value"] = frame["Corrected value"].astype("string")
    edited = st.data_editor(frame, hide_index=True, width="stretch",
                            disabled=True if disabled else ["Record", *columns],
                            column_config=configuration,
                            key=f"editor_{job['id']}_{category}_{field}")
    for position, index in enumerate(indices):
        value = edited.iloc[position]["Corrected value"]
        fields = drafts.setdefault(str(index), {})
        if pd.isna(value) or value == "":
            fields.pop(field, None)
        else:
            fields[field] = int(value) if field == "count" and float(value).is_integer() else value
        if not fields:
            drafts.pop(str(index), None)
    if "metric_type" in columns and any(
        str(drafts.get(str(index), {}).get("metric_type", job["records"][index].get("metric_type")) or "").strip().lower() == "unknown"
        for index in indices
    ):
        st.warning(
            "Metric type is unknown for one or more displayed records. The extraction could not "
            "establish whether the count represents a total on the register, new registrations, "
            "applications, or another measure. Check the source document and correct metric_type "
            "if the evidence supports it; otherwise leave it as unknown."
        )
    st.caption(f"{sum(len(fields) for fields in drafts.values())} corrected values across this upload.")
    return drafts
