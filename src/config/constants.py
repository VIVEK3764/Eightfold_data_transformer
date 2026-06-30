# Shared pipeline constants to avoid duplication across modules.

SOURCE_PRIORITY = {
    "resume": 1,
    "ats": 2,
    "csv": 3,
    "notes": 4
}

SOURCE_RELIABILITY = {
    "resume": 0.95,
    "ats": 0.90,
    "csv": 0.75,
    "notes": 0.60
}

# Identity resolution thresholds
NAME_SIMILARITY_THRESHOLD = 90.0
NAME_CONFLICT_SIMILARITY_THRESHOLD = 85.0
COMPANY_SIMILARITY_THRESHOLD = 85

# Confidence formula weights
CONFIDENCE_AGREEMENT_BONUS = 0.05
CONFIDENCE_CONFLICT_PENALTY = 0.10
