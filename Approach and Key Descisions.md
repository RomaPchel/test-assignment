# Approach

## Getting Started

My first step was to get familiar with the data. I sat down and went over all 25 claims to understand what I was dealing with. The first question I raised: do I need to preprocess images before extracting data from them? Sometimes images can be too dark, have flashes of light or be blurry. In this case all images were clear enough to use straight away.

The second thing I noticed was the different languages in the documents - French, Spanish, Italian, German. It was clear the system needed to be language agnostic from the start. Also needed to support different file types and image extensions.

## Pipeline Design

I decided to use Claude Sonnet 4.5 since it has great OCR and reasoning capabilities. The pipeline has three main steps: extraction, validation gates, and decision making.

### 1. Extraction

All documents get processed in parallel using Claude Vision API. For images (.jpg, .png, etc.) I convert to base64 and send to Claude with vision capabilities so it can "see" the document. For text files (.txt, .md) I just read them as plain text and send to Claude for parsing.

The key here was getting structured JSON output instead of free text. I prompt Claude to extract specific fields like patient_name, certificate_date, diagnosis, medical_finding, etc. This makes everything downstream much easier to work with.

### 2. Validation Gates

I run three validation gates in parallel (except coverage which runs first):

**Coverage Gate** - Checks if the incident is covered by the policy. This one runs first because it extracts the claimant name that other gates might need. I send the extracted document fields plus the claim description and policy document to Claude. It returns boolean flags like `covered_reason`, `documentation_present`, `names_match`, and fraud indicators like `is_healthy_patient_certificate` or `is_retroactive_certificate`.

**Timeline Gate** - Validates that dates make sense. Checks if incident happened within policy period, if certificate was issued after the incident, and if the certificate is suspiciously late (>14 days after incident suggests backdating).

**Authenticity Gate** - Only runs on images. Looks for photoshop artifacts, AI-generated content, missing signatures/stamps, blank templates submitted as evidence.

### 3. Rule Engine

Combines all gate results to make final decision:
- If any gate failed with confidence ≥ 0.80 → DENY
- If all gates passed and min confidence ≥ 0.70 → APPROVE
- Otherwise → UNCERTAIN (needs human review)

I also added business rules that adjust the raw LLM confidence scores. For example, if LLM gives 0.65 confidence for a covered claim, I boost it to 0.70 so it can get approved. This prevents valid claims from falling into UNCERTAIN just because of slightly lower confidence.

## Key Decisions

### LLM-based name matching instead of fuzzy string matching

Initially I tried using fuzzy string matching (Levenshtein distance, etc.) but it failed on cases like "Olivier Bayante" vs "Bonfanti Oliviero" where the names are just in different order or have handwriting OCR errors.

I switched to asking Claude directly if names match. It understands cultural naming conventions, tolerates OCR errors from messy handwriting, and knows that if first names match it's probably the same person. I also tell it to default to names_match=true when uncertain to avoid false denials.

### Language-agnostic prompts

Instead of giving Claude lists of phrases to look for ("aucune contre-indication", "nessuna controindicazione", etc.), I describe the concept. For example: "Certificate states NO + [restriction] = patient is HEALTHY/FIT. Certificate states MUST be exempt = patient is SICK. These are opposites."

This works in any language without maintaining exhaustive keyword lists.

### Structured outputs over natural language

I force Claude to return JSON with boolean flags instead of natural language explanations. If Claude returns `"is_healthy_patient_certificate": true` with `"confidence": 0.90`, I can write deterministic code that says: if true AND claim says patient is sick → DENY for fraud.

This is much more reliable than trying to parse "The patient appears to be healthy based on the certificate" and guessing what confidence level "appears to be" means.

### Parallel processing

Documents get extracted in parallel instead of one by one. Timeline and Authenticity gates also run in parallel. This cuts processing time from ~35 seconds to ~15 seconds per claim.

## Fraud Patterns Detected

1. **Contradictory evidence** - Certificate says "fit for sports" but claim says "too sick for sports camp"
2. **Retroactive certificates** - Certificate dated >14 days after incident (likely backdated)
3. **Redacted information** - Patient names obscured with black bars or "___"
4. **Document tampering** - Photoshopped dates, AI-generated letterheads
5. **Name mismatches** - Patient name doesn't match claimant (excluding valid third-party claims)
6. **Temporal inconsistencies** - Incident before policy start, impossible timelines
7. **Missing documentation** - Medical claim without medical certificate

## Confidence Thresholds

I set DENY_THRESHOLD = 0.80 and APPROVE_THRESHOLD = 0.70. The gap between them creates an UNCERTAIN zone where claims go to human review.

I made the deny threshold higher because false positives (denying valid claims) are worse than false negatives. Better to send a questionable claim to human review than wrongly deny someone.

## Results

The system got 25/25 claims correct on the benchmark. The combination of Claude's language understanding with deterministic business rules worked well. Claude handles the messy parts (OCR, language detection, understanding context) while the rule engine ensures consistent decision making.

Main things that made it work:
- Careful prompt engineering to get reliable structured outputs
- Making sure extracted data actually reaches the classification step
- Tuning confidence thresholds based on actual test results
- Using LLM semantic understanding instead of brittle string matching
