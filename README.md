# Insurance Claim Fraud Detection System

AI-powered claim validation using Claude Vision API and multi-gate validation.

> **See [Approach and Key Descisions.md](Approach%20and%20Key%20Descisions.md) for detailed explanation of design decisions and implementation details.**

## Performance

**96-100% accuracy** on benchmark (24-25/25 claims across multiple runs)

| Decision | Count | Precision | Recall |
|----------|-------|-----------|--------|
| APPROVE  | 7     | 100%      | 100%   |
| DENY     | 13    | 100%      | 100%   |
| UNCERTAIN| 5     | 100%      | 100%   |

**Note:** Minor variance (1-2 claims) may occur between runs due to probabilistic LLM outputs on borderline confidence cases.

## Setup

```bash
# Clone and install
git clone <your-repo-url>
cd takehome-assignment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env

# Run server
uvicorn app.main:app --reload
```

Server starts at `http://localhost:8000`

## API Usage

### POST /claims

```bash
curl -X POST http://localhost:8000/claims \
  -F "description=I had to cancel my trip due to sudden illness" \
  -F "files=@medical_certificate.jpg" \
  -F "files=@booking_confirmation.pdf"
```

**Request:**
- `description`: Claim description (10-10,000 chars)
- `files`: Supporting documents (1-20 files, max 10MB each)
- Supported types: `.jpg`, `.jpeg`, `.png`, `.pdf`, `.webp`, `.gif`, `.txt`, `.md`

**Response:**
```json
{
  "claim_id": "550e8400-e29b-41d4-a716-446655440000",
  "decision": "APPROVE",
  "confidence": 0.85,
  "reasoning": "Timeline verified. Coverage confirmed. Documentation authentic.",
  "gate_results": [...]
}
```

**Decisions:**
- `APPROVE`: All gates passed (confidence ≥ 0.70)
- `DENY`: Fraud detected or not covered (confidence ≥ 0.80)
- `UNCERTAIN`: Needs human review (confidence < 0.70)

### GET /claims/{claim_id}

Retrieve claim by ID.

### GET /claims

List all processed claims.

## How It Works

**Pipeline:** Extract → Validate → Decide

1. **Extraction** - Claude Vision extracts structured data from all documents (parallel)
2. **Validation Gates** (parallel):
   - **Coverage**: Policy check, name matching, fraud patterns
   - **Timeline**: Date consistency, retroactive certificates
   - **Authenticity**: Tampering, AI-generated content
3. **Rule Engine**: Combines results using confidence thresholds

## Fraud Detection

- Contradictory evidence (healthy certificate claiming illness)
- Retroactive certificates (>14 days after incident)
- Redacted information (obscured names)
- Document tampering (photoshopped, AI-generated)
- Name mismatches (patient ≠ claimant)
- Temporal inconsistencies (incident before policy start)
- Missing documentation

## Key Features

- **Language-agnostic**: Works with any language (French, Spanish, Italian, etc.)
- **LLM name matching**: Better than fuzzy matching for OCR errors and cultural variations
- **Structured outputs**: Boolean flags for deterministic decisions
- **Parallel processing**: ~15 second processing time per claim

## Running Tests

```bash
python eval/run_benchmark.py
```

Expected: `25/25 claims correct`

## Configuration

Edit `app/utils/business_rules.py`:

```python
APPROVE_THRESHOLD = 0.7   # Min confidence for approval
DENY_THRESHOLD = 0.8      # Min confidence for denial
PREMATURE_CLAIM_DAYS_THRESHOLD = 14  # Retroactive detection
```

## Project Structure

```
app/
├── api/routes.py          # API endpoints
├── core/
│   ├── extract.py         # Document extraction
│   ├── gates.py           # Validation gates
│   ├── pipeline.py        # Main pipeline
│   └── rule_engine.py     # Decision logic
├── prompts/               # LLM prompts
└── utils/                 # Config, logging, state

eval/
└── run_benchmark.py       # Test runner

data/
└── results.json           # Benchmark results
```

## Requirements

- Python 3.8+
- Anthropic API key
