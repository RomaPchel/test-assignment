from typing import Optional
from pydantic import BaseModel, Field

class ExtractedDocument(BaseModel):
    document_type: str
    source_language: str
    fields: dict = Field(default_factory=dict)
    raw_text: str
    extraction_confidence: float = Field(ge=0.0, le=1.0)

class GateResult(BaseModel):
    gate_name: str
    passed: bool
    confidence: float = Field(ge=0.0, le=1.0)
    signals: dict = Field(default_factory=dict)
    reason: str
    error: Optional[str] = None

class PipelineTrace(BaseModel):
    step: str
    model: Optional[str] = None
    model_version: Optional[str] = None
    latency_ms: float
