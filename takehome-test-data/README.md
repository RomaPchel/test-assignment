# MarvelX Home Assessment

Welcome! This take-home assignment is designed to simulate a real-world challenge at MarvelX: building an insurance claim processing pipeline.

This `README.md` explains the dataset structure and how it supports the task defined in the `Assignment.md`.

---

## 📁 What's Inside

This dataset contains 25 simulated insurance claims based on realistic customer scenarios, each with associated documentation and expected results.

- 25 claim folders
- answer.json files with expected outcomes
- Supporting documents in multiple formats

# Insurance Claims Benchmark Dataset

This directory contains the complete benchmark dataset for testing your claim processing pipeline - **25 insurance claims** from our benchmark system.

## Dataset Overview

- **25 claim directories** with realistic customer scenarios
- **25 answer.json files** with expected decisions and analysis
- **Supporting documents**: Medical certificates, police reports, flight records, receipts, court documents
- **Images**: 25 total including photos of documents, receipts, medical records

## Decision Distribution

- **9 APPROVE claims** (31%) - Valid claims with compensation amounts
- **15 DENY claims** (52%) - Claims not covered or invalid documentation  
- **5 UNCERTAIN claims** (17%) - Edge cases requiring human review or additional documentation

## Claim Types Included

### Medical Claims
- Hospital admissions and emergency treatments
- Surgery and medical procedure costs
- Medical certificates and discharge summaries
- Travel cancellations due to illness

### Travel Disruption Claims  
- Flight cancellations and missed connections
- Train delays and cancellations
- Hotel and accommodation issues
- Weather-related disruptions

### Legal Obligation Claims
- Jury duty summons
- Court appearances
- Mandatory legal proceedings

### Theft and Loss Claims
- Luggage theft at stations/airports
- Personal property loss
- Travel document theft

### Accident Claims
- Vehicle accidents preventing travel
- Personal injury incidents
- Emergency medical treatment

## File Structure

**Dataset Structure:**
- `policy.md` - Complete CFSR insurance policy with coverage rules and payout formulas
- `README.md` - This documentation file

Each claim directory contains:
- `description.txt` - Customer's claim description
- `answer.json` - Expected decision and reasoning
- Supporting documents:
  - `*.md` files - Medical certificates, flight data, booking records
  - `*.png/*.jpg/*.webp` - Photos of documents, receipts, medical records

## Usage Instructions

1. **Read the policy** - Start by reviewing `policy.md` to understand coverage rules
2. **Process all claims** through your pipeline according to the CFSR policy
3. **Compare results** with provided answer.json files
4. **Support multiple formats** - Your system should handle text and image documents
5. **Multilingual content** - Some claims include French, Spanish, Italian text

## Evaluation Criteria

Your system will be evaluated on:
- **Accuracy** of decisions vs. expected answers
- **Reasoning quality** in explanations
- **Document processing** capability across formats
- **Edge case handling** for unusual scenarios
- **Consistency** across similar claim types

## Expected Decisions

- **APPROVE** - Valid claims meeting policy requirements
- **DENY** - Claims not covered or invalid documentation  
- **UNCERTAIN** - Edge cases requiring human review

## Notes

- Claims represent plausible customer scenarios
- Some claims test edge cases and fraud detection
- Document quality varies intentionally (photos vs. official documents)
- Multiple languages and formats test system robustness