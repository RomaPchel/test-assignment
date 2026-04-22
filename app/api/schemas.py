from typing import Literal
from pydantic import BaseModel, Field
from app.models.schemas import GateResult, PipelineTrace

class ClaimSubmission(BaseModel):
    description: str
    metadata: dict = Field(default_factory=dict)

class ClaimDecision(BaseModel):
    claim_id: str
    decision: Literal["APPROVE", "DENY", "UNCERTAIN"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    gate_results: list[GateResult] = Field(default_factory=list)
    trace: list[PipelineTrace] = Field(default_factory=list)

class ClaimSummary(BaseModel):
    claim_id: str
    decision: Literal["APPROVE", "DENY", "UNCERTAIN"]
    confidence: float
