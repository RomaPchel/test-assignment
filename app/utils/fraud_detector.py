import json
from pathlib import Path
from typing import List

_fraud_rules_cache = None

def load_fraud_rules() -> dict:
    global _fraud_rules_cache

    if _fraud_rules_cache is None:
        config_path = Path(__file__).parent.parent.parent / "data" / "fraud_rules.json"

        try:
            with open(config_path, 'r') as f:
                _fraud_rules_cache = json.load(f)
        except FileNotFoundError:
            _fraud_rules_cache = {
                "severe_fraud_indicators": [],
                "critical_missing_date_indicators": [],
                "min_fraud_confidence_for_deny": 0.65
            }

    return _fraud_rules_cache

def get_severe_fraud_indicators() -> List[str]:
    rules = load_fraud_rules()
    return rules.get("severe_fraud_indicators", [])

def get_critical_date_indicators() -> List[str]:
    rules = load_fraud_rules()
    return rules.get("critical_missing_date_indicators", [])

def get_min_fraud_confidence() -> float:
    rules = load_fraud_rules()
    return rules.get("min_fraud_confidence_for_deny", 0.65)

def reload_fraud_rules():
    global _fraud_rules_cache
    _fraud_rules_cache = None
    load_fraud_rules()
