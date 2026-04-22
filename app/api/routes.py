from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import List
import re

from app.api.schemas import ClaimDecision, ClaimSummary
from app.core.pipeline import process_claim
from app.utils.state import save_claim_result, get_claim_result, CLAIMS

router = APIRouter()

MAX_DESCRIPTION_LENGTH = 10000
MIN_DESCRIPTION_LENGTH = 10
MAX_FILES = 20
MAX_FILE_SIZE_MB = 10
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf', '.webp', '.gif', '.txt', '.md'}

def validate_description(description: str) -> None:
    if not description or not description.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Description cannot be empty"
        )

    if len(description) < MIN_DESCRIPTION_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Description must be at least {MIN_DESCRIPTION_LENGTH} characters"
        )

    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Description cannot exceed {MAX_DESCRIPTION_LENGTH} characters"
        )

    if re.search(r'<script|javascript:|onclick=', description, re.IGNORECASE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Description contains invalid content"
        )

def validate_files(files: List[UploadFile]) -> None:
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one supporting document is required"
        )

    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot upload more than {MAX_FILES} files"
        )

    for file in files:
        file_ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if f'.{file_ext}' not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '.{file_ext}' not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        if hasattr(file, 'size') and file.size:
            if file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File '{file.filename}' exceeds {MAX_FILE_SIZE_MB}MB limit"
                )

@router.post("/claims", response_model=ClaimDecision, status_code=status.HTTP_201_CREATED)
async def create_claim(
    description: str = Form(...),
    files: List[UploadFile] = File(...)
):
    validate_description(description)
    validate_files(files)

    try:
        decision = await process_claim(description, files)
        save_claim_result(decision.claim_id, decision)
        return decision
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process claim. Please try again later."
        )

@router.get("/claims/{claim_id}", response_model=ClaimDecision)
async def get_claim(claim_id: str):
    result = get_claim_result(claim_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    return result

@router.get("/claims", response_model=List[ClaimSummary])
async def list_claims():
    return [ClaimSummary(claim_id=c.claim_id, decision=c.decision, confidence=c.confidence) for c in CLAIMS.values()]
