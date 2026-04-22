from typing import Optional
from pydantic import BaseModel, Field


class ExtractedDocument(BaseModel):
    document_type: str = Field(..., description="Type: medical_certificate, police_report, booking_confirmation, etc.")
    source_language: str = Field(..., description="Detected language code (en, fr, es, etc.)")
    fields: dict = Field(default_factory=dict, description="Extracted key-value pairs")
    raw_text: str = Field(..., description="Full extracted text content")
    extraction_confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence")


class GateResult(BaseModel):
    gate_name: str = Field(..., description="Name of the gate")
    passed: bool = Field(..., description="Whether gate passed")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Gate confidence")
    signals: dict = Field(default_factory=dict, description="Structured supporting data")
    reason: str = Field(..., description="Human-readable explanation")
    error: Optional[str] = Field(None, description="Error message if gate failed to execute")


class PipelineTrace(BaseModel):
    step: str = Field(..., description="Step name")
    inputs_hash: str = Field(..., description="Hash of input data")
    outputs_hash: str = Field(..., description="Hash of output data")
    model: Optional[str] = Field(None, description="Model used (null for Python-only)")
    model_version: Optional[str] = Field(None, description="Model version")
    latency_ms: float = Field(..., description="Execution time in milliseconds")
    cache_hit: bool = Field(False, description="Whether result was cached")
