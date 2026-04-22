import json
from pathlib import Path
from typing import Dict, Optional
from app.api.schemas import ClaimDecision
from app.utils.logger import logger

CLAIMS: Dict[str, ClaimDecision] = {}

STATE_FILE = Path(__file__).parent.parent.parent / "data" / "claim_results.json"

def _ensure_state_dir():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_state():
    global CLAIMS
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                CLAIMS = {
                    claim_id: ClaimDecision(**claim_data)
                    for claim_id, claim_data in data.items()
                }
        except Exception as e:
            logger.warning(f"Failed to load state: {e}")
            CLAIMS = {}
    else:
        CLAIMS = {}

def save_state():
    _ensure_state_dir()
    try:
        data = {
            claim_id: claim.model_dump() if hasattr(claim, 'model_dump') else claim.dict()
            for claim_id, claim in CLAIMS.items()
        }
        with open(STATE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save state: {e}")

def save_claim_result(claim_id: str, result: ClaimDecision):
    CLAIMS[claim_id] = result
    save_state()

def get_claim_result(claim_id: str) -> Optional[ClaimDecision]:
    if not CLAIMS:
        load_state()
    return CLAIMS.get(claim_id)

def clear_state():
    global CLAIMS
    CLAIMS = {}
    if STATE_FILE.exists():
        STATE_FILE.unlink()

load_state()
