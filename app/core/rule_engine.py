from typing import List, Tuple, Literal
from app.models.schemas import GateResult
from app.utils.config import APPROVE_THRESHOLD, DENY_THRESHOLD
from app.utils import business_rules as rules
from app.utils.fraud_detector import get_severe_fraud_indicators, get_critical_date_indicators, get_min_fraud_confidence

Decision = Literal["APPROVE", "DENY", "UNCERTAIN"]

def decide(gate_results: List[GateResult]) -> Tuple[Decision, float, str]:
    errors = [g for g in gate_results if g.error is not None]
    if errors:
        error_gates = ", ".join([g.gate_name for g in errors])
        return ("UNCERTAIN", 0.0, f"Processing errors in gate(s): {error_gates}. Unable to make determination.")

    coverage_gate = next((g for g in gate_results if g.gate_name == "coverage"), None)
    if coverage_gate and not coverage_gate.passed and coverage_gate.confidence >= DENY_THRESHOLD:
        return ("DENY", coverage_gate.confidence, f"DENY - coverage gate: {coverage_gate.reason} (confidence: {coverage_gate.confidence:.2f})")

    auth_gate = next((g for g in gate_results if g.gate_name == "authenticity"), None)
    if auth_gate and not auth_gate.passed:
        reason_lower = auth_gate.reason.lower()

        severe_fraud_indicators = get_severe_fraud_indicators()
        critical_missing_date_indicators = get_critical_date_indicators()
        min_fraud_confidence = get_min_fraud_confidence()

        matched_critical = [ind for ind in critical_missing_date_indicators if ind in reason_lower]
        if matched_critical:
            return ("DENY", max(auth_gate.confidence, 0.85), f"DENY - authenticity gate: Critical information missing on official document. {auth_gate.reason}")

        if any(indicator in reason_lower for indicator in severe_fraud_indicators):
            if auth_gate.confidence >= min_fraud_confidence:
                return ("DENY", auth_gate.confidence, f"DENY - authenticity gate: Document is invalid or tampered. {auth_gate.reason} (confidence: {auth_gate.confidence:.2f})")

        if auth_gate.confidence >= 0.70:
            combined_confidence = min(g.confidence for g in gate_results)
            return ("UNCERTAIN", combined_confidence, f"Authenticity concerns detected: {auth_gate.reason}. Manual review recommended.")

    if auth_gate and auth_gate.passed:
        document_category = auth_gate.signals.get("document_category", "other")

        if document_category == "medical":
            has_sig = auth_gate.signals.get("has_signature", True)
            has_stamp = auth_gate.signals.get("has_stamp", True)

            if not has_sig and not has_stamp:
                combined_confidence = min(g.confidence for g in gate_results)
                return ("UNCERTAIN", combined_confidence, "Medical certificate has letterhead but lacks doctor's signature and official stamp. Manual verification required.")

    if coverage_gate and not coverage_gate.signals.get("names_match", True):
        is_third_party = coverage_gate.signals.get("is_third_party_claim", False)
        if not is_third_party:
            combined_confidence = min(g.confidence for g in gate_results)
            claimant = coverage_gate.signals.get("claimant_name", "")
            patient = coverage_gate.signals.get("patient_name_from_documents", "")
            return ("UNCERTAIN", combined_confidence, f"Name mismatch detected: claimant '{claimant}' vs patient '{patient}'. Manual review required. {coverage_gate.reason}")

    if coverage_gate and coverage_gate.signals.get("is_premature_claim"):
        combined_confidence = min(g.confidence for g in gate_results)
        return ("UNCERTAIN", combined_confidence, f"Claim filed prematurely before travel date. Manual review needed to determine if condition will persist. {coverage_gate.reason}")

    if coverage_gate and coverage_gate.signals.get("uncertain_prognosis"):
        combined_confidence = min(g.confidence for g in gate_results)
        return ("UNCERTAIN", combined_confidence, f"Patient is currently hospitalized but travel date is in the future. Manual review needed to determine if condition will persist until travel date. {coverage_gate.reason}")

    if coverage_gate and coverage_gate.signals.get("is_retroactive_certificate"):
        combined_confidence = min(g.confidence for g in gate_results)
        return ("UNCERTAIN", combined_confidence, f"Medical certificate issued >14 days after incident - possible backdated document. Manual review required to verify authenticity. {coverage_gate.reason}")

    timeline_gate = next((g for g in gate_results if g.gate_name == "timeline"), None)
    if timeline_gate and timeline_gate.signals.get("may_be_premature"):
        combined_confidence = min(g.confidence for g in gate_results)
        return ("UNCERTAIN", combined_confidence, f"Claim filed {timeline_gate.signals.get('days_until_travel')} days before travel. Manual review needed to confirm ongoing condition. {timeline_gate.reason}")

    failed_gates = [g for g in gate_results if not g.passed and g.gate_name != "authenticity" and g.confidence >= DENY_THRESHOLD]
    if failed_gates:
        gate = failed_gates[0]
        combined_confidence = min(g.confidence for g in gate_results)
        return ("DENY", combined_confidence, f"DENY - {gate.gate_name} gate: {gate.reason} (confidence: {gate.confidence:.2f})")

    all_passed = all(g.passed for g in gate_results)
    combined_confidence = min(g.confidence for g in gate_results)

    if all_passed and combined_confidence >= APPROVE_THRESHOLD:
        gate_summaries = ", ".join([f"{g.gate_name}({g.confidence:.2f})" for g in gate_results])
        return ("APPROVE", combined_confidence, f"APPROVE - All validation gates passed: {gate_summaries}")

    failed_gate_names = [g for g in gate_results if not g.passed]
    if failed_gate_names:
        max_failed_confidence = max((g.confidence for g in failed_gate_names), default=0.0)
        if max_failed_confidence < 0.70:
            return ("UNCERTAIN", combined_confidence, f"Mixed signals: gate(s) {', '.join([g.gate_name for g in failed_gate_names])} failed with low confidence. Manual review recommended.")
        else:
            return ("UNCERTAIN", combined_confidence, f"Mixed signals: gate(s) {', '.join([g.gate_name for g in failed_gate_names])} failed. Manual review recommended.")
    else:
        return ("UNCERTAIN", combined_confidence, f"Low confidence (min: {combined_confidence:.2f} < threshold: {APPROVE_THRESHOLD}). Manual review recommended.")
