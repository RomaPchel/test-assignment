APPROVE_THRESHOLD = 0.7
DENY_THRESHOLD = 0.8

THRESHOLD_FRAUD_DENIAL = 0.75
THRESHOLD_COVERAGE_DENIAL = 0.85
THRESHOLD_PREMATURE_UNCERTAIN = 0.6
THRESHOLD_TEMPORAL_UNCERTAIN = 0.65
THRESHOLD_CLEAN_APPROVAL = 0.7

CONFIDENCE_MISSING_DATA = 0.75
CONFIDENCE_MISSING_DOCS = 0.95
CONFIDENCE_PREMATURE_CLAIM = 0.7
CONFIDENCE_NO_TAMPERING = 0.7

CONFIDENCE_CAP_SEVERE_FRAUD = 0.85
CONFIDENCE_CAP_MODERATE_ISSUES = 0.70

TAMPERING_MIN_CONFIDENCE = 0.6

ENABLE_ENSEMBLE_VOTING = False
ENSEMBLE_SAMPLES = 3

NAME_SIMILARITY_THRESHOLD = 0.60
LEVENSHTEIN_MAX_DISTANCE = 2
MIN_PART_LENGTH_FOR_FUZZY = 4
REQUIRE_COMMON_PARTS_COUNT = 2

MIN_NAME_LENGTH = 3

PREMATURE_CLAIM_DAYS_THRESHOLD = 14

INCIDENT_DATE_FIELDS = [
    'incident_date', 'emergency_date', 'event_date', 'date', 'departure'
]

POLICY_START_FIELDS = [
    'booking_date', 'travel_date', 'start_date', 'booked_on',
    'booked on', 'departure', 'departure_date'
]

POLICY_END_FIELDS = [
    'end_date', 'return_date', 'return'
]

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
TEXT_EXTENSIONS = {'.txt', '.md', '.doc', '.docx'}

MEDICAL_DOC_TYPES = [
    'medical_certificate', 'hospital_discharge', 'medical_report',
    'doctor_note', 'hospital_admission'
]

COMMERCIAL_DOC_TYPES = [
    'receipt', 'booking_confirmation', 'invoice', 'ticket', 'flight_record'
]

NAME_FIELDS = ['name', 'customer_name', 'patient_name', 'passenger_name']
DATE_FIELDS = [
    'booking_date', 'travel_date', 'incident_date', 'date', 'discharge_date',
    'admission_date', 'emergency_date', 'event_date'
]
AMOUNT_FIELDS = ['amount', 'total', 'price', 'cost']

INVALID_VALUE_INDICATORS = ['', 'N/A', 'n/a', 'null', 'None', '___', '---', 'blank']

SEVERE_FRAUD_INDICATORS = [
    "not a relevant official document",
    "not a document",
    "photograph/selfie",
    "photo/selfie",
    "ai-generated",
    "fake document",
    "completely fabricated",
    "unrelated content",
    "critical information (name, dates) is redacted or obscured",
    "redacted or obscured",
    "unfilled template",
    "blank template",
    "blank date fields",
    "empty doctor information",
    "appears to be an unfilled template",
    "missing discharge date",
    "missing critical dates",
    "critical information missing"
]

MIN_FRAUD_CONFIDENCE_FOR_DENY = 0.65

AMOUNT_VARIANCE_TOLERANCE = 0.01

MIN_DOCUMENTS_FOR_CONSISTENCY = 2

SINGLE_NAME_MISMATCH_CONFIDENCE = 0.7
MINOR_MISMATCH_CONFIDENCE = 0.75
HIGH_SEVERITY_MISMATCH_CONFIDENCE = 0.85

MAX_MINOR_MISMATCHES = 2

def get_coverage_confidence(llm_confidence: float, covered: bool, is_premature: bool) -> float:
    if is_premature:
        return CONFIDENCE_PREMATURE_CLAIM

    if covered:
        if llm_confidence >= 0.9:
            return 0.9
        elif llm_confidence >= 0.7:
            return 0.75
        elif llm_confidence >= 0.6:
            return 0.7
        else:
            return 0.5
    else:
        if llm_confidence >= 0.8:
            return 0.9
        else:
            return 0.7

GATE_TIMEOUT_SECONDS = 30
EXTRACTION_TIMEOUT_SECONDS = 45
