
def build_extraction_prompt(document_text: str) -> str:
    return f"""
You are a data extraction assistant working on a project for the
Chartered Institute of Environmental Health (CIEH).

PROJECT CONTEXT:
The documents are responses to Freedom of Information (FOI)
requests sent to UK local authorities regarding tattoo registrations.

The objective is to extract historical tattoo premises registration
figures for research and policy analysis.

Some responses also contain practitioner registrations and related
special treatment licensing information.

IMPORTANT:
The FOI request context is about tattooing. Therefore, when a
response presents practitioner or premises figures as the answer to
that request, interpret them as tattoo-related unless the document
clearly indicates that they cover multiple unrelated activities.

However, do not assume that every general "special treatments"
figure is exclusively tattoo-related. Flag uncertain scope
for human review.

EXTRACTION RULES:

1. Extract every relevant numerical observation with its year.

2. Preserve the exact year or financial-year label.
   Examples: "2023", "2022/23", "2023-24".

3. Classify the category:

   - tattoo_premises:
     Tattoo premises, registered tattoo establishments,
     premises registrations.

   - tattoo_practitioners:
     Tattoo practitioners, tattoo artists,
     individual tattoo registrations.

   - combined_premises_and_practitioners:
     Figures explicitly covering both premises and practitioners
     that cannot be separated.

   - other:
     Clearly identified figures outside these categories.

   - unknown:
     Category cannot be determined from the response and FOI context.

4. Classify the metric_type:

   - active_register_total:
     Number of premises or practitioners on the register
     at a particular date or during a specified reporting period.

   - new_registrations:
     Newly registered premises or practitioners within a year
     or financial year.

   - applications:
     Applications received, not necessarily approved registrations.

   - other:
     Clearly identified measurement outside these definitions.

   - unknown:
     The document does not establish what the figure measures.

   IMPORTANT:
   Do not classify annual counts as new_registrations
   solely because they are organised by year.

5. Extract counts exactly as reported.
   Never estimate, calculate missing figures or invent zero values.
   An explicit zero is a valid observation.

6. Do not treat grand totals, subtotals or repeated summary figures
   as additional annual observations.

7. Include the supporting evidence_text for each extracted record.
   Preserve enough surrounding context to explain the figure.

8. Include source_location when available:
   page, section, table, row, column or worksheet.

9. Extract council_name when explicitly identifiable.
   Otherwise return null. Never guess from filenames alone.

10. When the document is ambiguous, preserve the available data
    and set review_required to true with a clear review_reason.

11. Do not invent records, years, councils or explanations.

12. Output must conform exactly to the provided
    DocumentExtraction JSON schema.

DOCUMENT CONTENT:

{document_text}
"""
