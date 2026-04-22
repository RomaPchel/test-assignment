from typing import Literal
from pydantic import BaseModel, Field
from app.models.schemas import GateResult, PipelineTrace


class ClaimSubmission(BaseModel):
    description: str = Field(..., description="Customer's claim description")
    metadata: dict = Field(default_factory=dict, description="Optional claim metadata")


class ClaimDecision(BaseModel):
    claim_id: str = Field(..., description="Unique claim identifier")
    decision: Literal["APPROVE", "DENY", "UNCERTAIN"] = Field(..., description="Final decision")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Combined confidence score")
    reasoning: str = Field(..., description="Human-readable explanation")
    gate_results: list[GateResult] = Field(default_factory=list, description="Individual gate outcomes")
    trace: list[PipelineTrace] = Field(default_factory=list, description="Execution trace")


class ClaimSummary(BaseModel):
    claim_id: str
    decision: Literal["APPROVE", "DENY", "UNCERTAIN"]
    confidence: float
