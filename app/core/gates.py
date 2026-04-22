import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import anthropic

from app.models.schemas import ExtractedDocument, GateResult, PipelineTrace
from app.utils.config import ANTHROPIC_API_KEY, GATE_TIMEOUT_SECONDS, MODEL_NAME
from app.utils import business_rules as rules

def _read_prompt(prompt_name: str) -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / f"{prompt_name}.txt"
    return prompt_path.read_text()

def _read_policy() -> str:
    policy_path = Path(__file__).parent.parent.parent / "data" / "policy.txt"
    return policy_path.read_text()

def _extract_date_from_text(text: str) -> Optional[datetime]:
    patterns = [
        (r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', lambda m: datetime(int(m[1]), int(m[2]), int(m[3]))),
        (r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', lambda m: datetime(int(m[3]), int(m[1]), int(m[2]))),
        (r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b',
         lambda m: datetime.strptime(f"{m[1]} {m[2]} {m[3]}", "%B %d %Y")),
        (r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b',
         lambda m: datetime.strptime(f"{m[2]} {m[1]} {m[3]}", "%B %d %Y")),
    ]
    for pattern, parser in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return parser(match.groups())
            except (ValueError, IndexError):
                continue
    return None

async def timeline_gate(extracted_docs: List[ExtractedDocument], claim_description: str) -> Tuple[GateResult, PipelineTrace]:
    start_time = time.time()
    
    incident_date: Optional[datetime] = None
    policy_start: Optional[datetime] = None
    policy_end: Optional[datetime] = None

    incident_date = _extract_date_from_text(claim_description)

    for doc in extracted_docs:
        if not incident_date:
            for key in ['incident_date', 'emergency_date', 'event_date', 'date', 'departure']:
                if key in doc.fields and doc.fields[key]:
                    incident_date = _extract_date_from_text(str(doc.fields[key]))
                    if incident_date:
                        break
            if not incident_date and doc.raw_text:
                incident_date = _extract_date_from_text(doc.raw_text)

        if not policy_start:
            for key in ['booking_date', 'travel_date', 'start_date', 'booked_on', 'booked on', 'departure', 'departure_date']:
                if key in doc.fields and doc.fields[key]:
                    policy_start = _extract_date_from_text(str(doc.fields[key]))
                    if policy_start:
                        break
            if not policy_start and doc.raw_text:
                booked_match = re.search(r'booked\s+on[:\s]+(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})', doc.raw_text, re.IGNORECASE)
                if booked_match:
                    policy_start = _extract_date_from_text(booked_match.group(1))

        if not policy_end:
            for key in ['end_date', 'return_date', 'return']:
                if key in doc.fields and doc.fields[key]:
                    policy_end = _extract_date_from_text(str(doc.fields[key]))
                    if policy_end:
                        break
    
    if not incident_date:
        result = GateResult(
            gate_name="timeline",
            passed=True,
            confidence=rules.CONFIDENCE_MISSING_DATA,
            signals={"incident_date": None, "policy_start": str(policy_start) if policy_start else None, "policy_end": str(policy_end) if policy_end else None, "within_window": None},
            reason="Unable to extract incident date - assuming valid timeline"
        )
    elif not policy_start:
        result = GateResult(
            gate_name="timeline",
            passed=True,
            confidence=rules.CONFIDENCE_MISSING_DATA,
            signals={"incident_date": str(incident_date), "policy_start": None, "policy_end": None, "within_window": None},
            reason=f"Found incident date {incident_date.date()} but unable to determine policy period - assuming valid"
        )
    else:
        if policy_end:
            within_window = policy_start <= incident_date <= policy_end
        else:
            within_window = incident_date >= policy_start

        current_date = None
        current_date_match = re.search(r'current\s+date\s+is[:\s]+(\d{4}-\d{2}-\d{2})', claim_description, re.IGNORECASE)
        if current_date_match:
            current_date = _extract_date_from_text(current_date_match.group(1))

        if not current_date:
            for doc in extracted_docs:
                if doc.raw_text:
                    current_date_match = re.search(r'current\s+date\s+is[:\s]+(\d{4}-\d{2}-\d{2})', doc.raw_text, re.IGNORECASE)
                    if current_date_match:
                        current_date = _extract_date_from_text(current_date_match.group(1))
                        break

        if current_date:
            if current_date and policy_start:
                travel_date = policy_start
                days_until_travel = (travel_date - current_date).days

                if days_until_travel > rules.PREMATURE_CLAIM_DAYS_THRESHOLD:
                    result = GateResult(
                        gate_name="timeline",
                        passed=True,
                        confidence=rules.CONFIDENCE_PREMATURE_CLAIM,
                        signals={"incident_date": str(incident_date.date()), "travel_date": str(travel_date.date()), "current_date": str(current_date.date()), "days_until_travel": days_until_travel, "may_be_premature": True},
                        reason=f"Claim filed {days_until_travel} days before travel. Manual review recommended to confirm condition will persist."
                    )
                    trace = PipelineTrace(step="timeline_gate", inputs_hash="", outputs_hash="", model=None, model_version=None, latency_ms=(time.time() - start_time) * 1000, cache_hit=False)
                    return result, trace

        result = GateResult(
            gate_name="timeline",
            passed=within_window,
            confidence=1.0 if within_window else 0.95,
            signals={"incident_date": str(incident_date.date()), "policy_start": str(policy_start.date()), "policy_end": str(policy_end.date()) if policy_end else None, "within_window": within_window},
            reason=f"Incident date {incident_date.date()} {'falls within' if within_window else 'is outside'} policy period ({policy_start.date()} to {policy_end.date() if policy_end else 'ongoing'})"
        )
    
    trace = PipelineTrace(step="timeline_gate", inputs_hash="", outputs_hash="", model=None, model_version=None, latency_ms=(time.time() - start_time) * 1000, cache_hit=False)
    return result, trace

async def coverage_gate(extracted_docs: List[ExtractedDocument], claim_description: str, file_paths: List[str] = None) -> Tuple[GateResult, PipelineTrace]:
    start_time = time.time()

    try:
        incident_type_check = None
        desc_lower = claim_description.lower()
        if any(kw in desc_lower for kw in ['medical', 'emergency', 'illness', 'hospital', 'doctor']):
            incident_type_check = "medical"
        elif any(kw in desc_lower for kw in ['theft', 'stolen', 'robbery']):
            incident_type_check = "theft"

        if incident_type_check and file_paths:
            medical_docs = []
            for fp in file_paths:
                ext = Path(fp).suffix.lower()
                if ext in rules.IMAGE_EXTENSIONS:
                    medical_docs.append((fp, 'image'))
                elif ext in rules.TEXT_EXTENSIONS:
                    medical_docs.append((fp, 'text'))

            if incident_type_check == "medical" and medical_docs:
                has_valid_medical = any(doc_type == 'image' for _, doc_type in medical_docs)
                has_only_text = all(doc_type == 'text' for _, doc_type in medical_docs)

                if has_only_text:
                    result = GateResult(
                        gate_name="coverage",
                        passed=False,
                        confidence=rules.CONFIDENCE_MISSING_DOCS,
                        signals={"incident_type": "medical", "invalid_document_format": "text_only", "covered_reason": False},
                        reason="Medical documentation provided in plain text format (.txt/.md) is not acceptable. Medical certificates must be official documents (images/PDFs) with letterhead, stamps, and signatures."
                    )
                    trace = PipelineTrace(step="coverage_gate", inputs_hash="", outputs_hash="", model=None, model_version=None, latency_ms=(time.time() - start_time) * 1000, cache_hit=False)
                    return result, trace

            if incident_type_check == "medical" and not medical_docs:
                desc_lower = claim_description.lower()
                should_have_docs = any(phrase in desc_lower for phrase in [
                    "attach", "enclosed", "certificate", "medical", "hospital", "doctor", "emergency"
                ])
                docs_promised = any(phrase in desc_lower for phrase in ["upon request", "can provide", "available"])

                if should_have_docs or docs_promised:
                    result = GateResult(
                        gate_name="coverage",
                        passed=False,
                        confidence=rules.CONFIDENCE_MISSING_DOCS,
                        signals={"incident_type": "medical", "documentation_present": False, "covered_reason": False},
                        reason="Claim describes medical emergency but no medical documentation (certificate, hospital records) was submitted. Required documentation is missing."
                    )
                    trace = PipelineTrace(step="coverage_gate", inputs_hash="", outputs_hash="", model=None, model_version=None, latency_ms=(time.time() - start_time) * 1000, cache_hit=False)
                    return result, trace

        system_prompt = _read_prompt("classify_incident")
        policy_text = _read_policy()
        doc_summaries = []
        for i, doc in enumerate(extracted_docs):
            summary = f"Document {i+1} ({doc.document_type}):"
            if doc.fields:
                key_fields = {k: v for k, v in doc.fields.items() if k in ['incident_date', 'certificate_date', 'document_date', 'patient_name', 'diagnosis', 'medical_finding', 'discharge_date', 'admission_date']}
                if key_fields:
                    summary += f" [Extracted fields: {key_fields}]"
            summary += f" {doc.raw_text[:300]}..."
            doc_summaries.append(summary)
        doc_summaries = "\n".join(doc_summaries)

        prompt = system_prompt.replace("{policy_text}", policy_text).replace("{claim_description}", claim_description).replace("{document_summaries}", doc_summaries)

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
            timeout=GATE_TIMEOUT_SECONDS
        )

        response_text = message.content[0].text
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        data = json.loads(response_text[json_start:json_end])

        raw_confidence = data["confidence"]
        documentation_present = data.get("documentation_present", True)
        covered_reason = data["covered_reason"]
        reasoning = data.get("reasoning", "")

        names_match = data.get("names_match", True)
        is_premature_claim = data.get("is_premature_claim", False)
        is_healthy_patient = data.get("is_healthy_patient_certificate", False)
        is_retroactive_cert = data.get("is_retroactive_certificate", False)
        has_temporal_discrepancy = data.get("has_minor_temporal_discrepancy", False)
        uncertain_prognosis = data.get("uncertain_prognosis", False)

        if not covered_reason and has_temporal_discrepancy:
            covered_reason = True

        if not documentation_present:
            confidence = rules.CONFIDENCE_MISSING_DOCS
            passed = False
        elif not covered_reason and is_healthy_patient:
            confidence = 0.85
            passed = False
        elif not covered_reason and not is_premature_claim:
            confidence = 0.9 if raw_confidence >= 0.8 else 0.7
            passed = False
        elif not covered_reason and is_premature_claim:
            confidence = rules.CONFIDENCE_PREMATURE_CLAIM
            passed = True
        else:
            confidence = rules.get_coverage_confidence(raw_confidence, covered_reason, is_premature_claim)
            passed = True

        result = GateResult(
            gate_name="coverage",
            passed=passed,
            confidence=confidence,
            signals={
                "incident_type": data["incident_type"],
                "covered_reason": data["covered_reason"],
                "documentation_present": documentation_present,
                "policy_section": data["policy_section"],
                "names_match": names_match,
                "is_third_party_claim": data.get("is_third_party_claim", False),
                "claimant_name": data.get("claimant_name", ""),
                "patient_name_from_documents": data.get("patient_name_from_documents", ""),
                "is_premature_claim": is_premature_claim,
                "has_temporal_discrepancy": has_temporal_discrepancy,
                "uncertain_prognosis": uncertain_prognosis,
                "is_retroactive_certificate": is_retroactive_cert
            },
            reason=data["reasoning"]
        )
    except Exception as e:
        result = GateResult(gate_name="coverage", passed=False, confidence=0.0, signals={}, reason="Gate execution error", error=str(e))
    
    trace = PipelineTrace(step="coverage_gate", inputs_hash="", outputs_hash="", model=MODEL_NAME, model_version=MODEL_NAME, latency_ms=(time.time() - start_time) * 1000, cache_hit=False)
    return result, trace

async def _check_single_image(img_path: str, system_prompt: str, client: anthropic.Anthropic) -> dict:
    import base64
    from PIL import Image

    try:
        with Image.open(img_path) as img:
            fmt = img.format.lower() if img.format else "jpeg"
            media_type_map = {"png": "image/png", "jpeg": "image/jpeg", "jpg": "image/jpeg", "webp": "image/webp"}
            media_type = media_type_map.get(fmt, "image/jpeg")

        with open(img_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        message = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                {"type": "text", "text": "Analyze this document image for signs of tampering."}
            ]}],
            timeout=GATE_TIMEOUT_SECONDS
        )

        response_text = message.content[0].text
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        data = json.loads(response_text[json_start:json_end])

        document_is_relevant = data.get("document_is_relevant", True)
        tampered = data["tampered"]
        redacted_info = data.get("redacted_info", False)

        is_severe_fraud = (
            not document_is_relevant or
            redacted_info or
            "blank template" in response_text.lower() or
            "unfilled template" in response_text.lower() or
            "empty doctor information" in response_text.lower()
        )

        confidence_cap = rules.CONFIDENCE_CAP_SEVERE_FRAUD if is_severe_fraud else rules.CONFIDENCE_CAP_MODERATE_ISSUES
        img_confidence = min(data["confidence"], confidence_cap)

        return {
            "success": True,
            "img_path": img_path,
            "tampered": tampered,
            "confidence": img_confidence,
            "artifacts": data["artifacts"],
            "document_category": data.get("document_category", "other"),
            "has_signature": data.get("has_signature", True),
            "has_stamp": data.get("has_stamp", True),
            "has_letterhead": data.get("has_letterhead", True),
            "document_is_relevant": document_is_relevant,
            "redacted_info": redacted_info,
            "is_severe_fraud": is_severe_fraud
        }
    except Exception as e:
        return {
            "success": False,
            "img_path": img_path,
            "error": str(e)
        }

async def authenticity_gate(image_paths: List[str]) -> Tuple[GateResult, PipelineTrace]:
    start_time = time.time()

    if not image_paths:
        result = GateResult(
            gate_name="authenticity",
            passed=True,
            confidence=1.0,
            signals={"images_checked": 0},
            reason="No images to verify"
        )
        trace = PipelineTrace(step="authenticity_gate", inputs_hash="", outputs_hash="", model=MODEL_NAME, model_version=MODEL_NAME, latency_ms=(time.time() - start_time) * 1000, cache_hit=False)
        return result, trace

    system_prompt = _read_prompt("authenticity_check")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    tasks = [_check_single_image(img_path, system_prompt, client) for img_path in image_paths]
    results = await asyncio.gather(*tasks)

    tampering_detected = False
    max_confidence = 0.0
    all_artifacts = []
    document_categories = []
    has_any_signature = False
    has_any_stamp = False

    for result in results:
        if not result["success"]:
            all_artifacts.append(f"Error checking {result['img_path']}: {result['error']}")
            continue

        img_path = result["img_path"]
        document_category = result["document_category"]
        document_categories.append(document_category)

        if result["has_signature"]:
            has_any_signature = True
        if result["has_stamp"]:
            has_any_stamp = True

        if not result["document_is_relevant"]:
            all_artifacts.append(f"{Path(img_path).name}: Submitted file is not a relevant official document (appears to be photo/selfie/AI-generated/unrelated content)")
            tampering_detected = True
            max_confidence = max(max_confidence, 0.9)

        if document_category == "medical" and not result["has_signature"] and not result["has_stamp"]:
            all_artifacts.append(f"{Path(img_path).name}: Medical certificate lacks both signature and official stamp (only letterhead present)")
            tampering_detected = True
            max_confidence = max(max_confidence, 0.75)

        if result["redacted_info"]:
            all_artifacts.append(f"{Path(img_path).name}: Critical information (name, dates) is redacted or obscured")
            tampering_detected = True
            max_confidence = max(max_confidence, 0.8)

        if result["tampered"] and result["confidence"] >= rules.TAMPERING_MIN_CONFIDENCE:
            tampering_detected = True
            all_artifacts.extend(result["artifacts"])
            max_confidence = max(max_confidence, result["confidence"])

    primary_category = document_categories[0] if document_categories else "other"

    if tampering_detected:
        gate_result = GateResult(
            gate_name="authenticity",
            passed=False,
            confidence=min(max_confidence, 0.7),
            signals={
                "images_checked": len(image_paths),
                "tampering_detected": True,
                "artifacts": all_artifacts,
                "has_signature": has_any_signature,
                "has_stamp": has_any_stamp,
                "document_category": primary_category
            },
            reason=f"Potential tampering detected. Artifacts: {', '.join(all_artifacts)}"
        )
    else:
        gate_result = GateResult(
            gate_name="authenticity",
            passed=True,
            confidence=rules.CONFIDENCE_NO_TAMPERING,
            signals={
                "images_checked": len(image_paths),
                "tampering_detected": False,
                "artifacts": [],
                "has_signature": has_any_signature,
                "has_stamp": has_any_stamp,
                "document_category": primary_category
            },
            reason=f"No obvious tampering detected in {len(image_paths)} image(s)"
        )

    trace = PipelineTrace(step="authenticity_gate", inputs_hash="", outputs_hash="", model=MODEL_NAME, model_version=MODEL_NAME, latency_ms=(time.time() - start_time) * 1000, cache_hit=False)
    return gate_result, trace
