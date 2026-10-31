from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class ExtractionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    year: str | None = None
    category: Literal[
        "tattoo_premises",
        "tattoo_practitioners",
        "combined_premises_and_practitioners",
        "other",
        "unknown"
    ]
    metric_type: Literal[
        "active_register_total",
        "new_registrations",
        "applications",
        "other",
        "unknown"
    ]
    count: int = Field(ge=0)
    evidence_text: str
    source_location: str | None = None
    notes: str | None = None

class DocumentExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    council_name: str | None = None
    records: list[ExtractionRecord] = Field(default_factory=list)
    review_required: bool = False
    review_reason: str | None = None
