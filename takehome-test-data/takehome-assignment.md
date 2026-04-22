# Insurance Claim Processing Pipeline - Take-Home Assignment

## Overview

You are tasked with building a claim processing pipeline that analyzes insurance claims and makes coverage decisions. This assignment is based on claims data from our internal benchmark.

Your solution should process insurance claims with supporting documents and determine whether claims should be **APPROVED**, **DENIED**, or marked as **UNCERTAIN**.

## Assignment Requirements

### Core Functionality

Build a system that:

1. **Accepts claim submissions** with:
   - Text description of the incident
   - Supporting documents (images, medical certificates, etc.)
   - Metadata (dates, names, etc.)

2. **Processes claims** by analyzing the submitted information and documents

3. **Makes decisions** and provides:
   - Final decision (APPROVE/DENY/UNCERTAIN)
   - Reasoning for the decision

### Technical Requirements

- **Language**: Python 3.9+
- **Framework**: FastAPI or Flask for API endpoints
- **File Processing**: Handle image and text document formats
- **API Design**: RESTful endpoints for claim submission and retrieval

### Expected Deliverables

1. **Working API** with endpoints:
   - `POST /claims` - Submit a new claim
   - `GET /claims/{claim_id}` - Retrieve claim decision
   - `GET /claims` - List all processed claims

2. **Documentation**:
   - README with setup instructions
   - API documentation
   - Brief explanation of your decision-making logic

3. **Test Results**: Process the complete benchmark dataset (25 claims) and include your system's outputs with performance metrics

### Exclusions
- Claims with suspicious or altered documentation
- Incidents outside the coverage timeline
- Events not covered by the policy terms

## Bonus Points

- **Confidence Scoring**: Provide confidence levels for decisions
- **Document Processing**: Extract and analyze text from images
- **Fraud Detection**: Basic checks for document authenticity


## Time Expectation

This assignment should take **4~ hours** to complete:

## Submission

Please provide:
1. **Source code** (GitHub repository preferred)
2. **README** with setup and run instructions
3. **Results file** showing your system's analysis of each test claim
4. **Brief explanation** of your approach and any assumptions made

## Questions?

If you have questions about the assignment scope or requirements, please reach out. Good luck!

---

*This assignment is based on a real claim processing system and represents the types of challenges you'd work on in this role.* 