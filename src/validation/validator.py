import re
import json
from typing import Any, Dict
from src.models.candidate import Candidate
from src.validation.validation_result import ValidationResult

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
PHONE_E164_REGEX = re.compile(r"^\+[1-9]\d{1,14}$")
PATH_PART_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\[\]|\[\d+\])?$")


def validate_candidate(candidate: Any) -> ValidationResult:
    """
    Validates a Candidate object for correct structure, valid formats, and bounds.
    Returns a ValidationResult listing every detected problem.
    """
    res = ValidationResult()

    if candidate is None:
        res.add_error("Candidate object is missing")
        return res

    # Candidate ID
    if not getattr(candidate, "candidate_id", None):
        res.add_error("Candidate missing candidate_id")

    # full_name warning (not a hard error, but noteworthy)
    if not getattr(candidate, "full_name", None):
        res.add_error("Candidate missing full_name")

    # Emails
    for email in getattr(candidate, "emails", []) or []:
        if not EMAIL_REGEX.match(email):
            res.add_error(f"Invalid email: {email}")

    # Phones
    for phone in getattr(candidate, "phones", []) or []:
        if not PHONE_E164_REGEX.match(phone):
            res.add_error(f"Invalid phone: {phone}")

    # years_experience — must be non-negative when present (Fix 6)
    years_exp = getattr(candidate, "years_experience", None)
    if years_exp is not None and years_exp < 0:
        res.add_error(f"years_experience must be non-negative, got {years_exp}")

    # Overall confidence bounds
    overall_conf = getattr(candidate, "overall_confidence", 0.0)
    if not (0.0 <= overall_conf <= 1.0):
        res.add_error("Confidence out of range")

    # Skill-level checks (Fix 6: also check for empty skill names)
    for skill in getattr(candidate, "skills", []) or []:
        if not getattr(skill, "name", "").strip():
            res.add_error("Skill has empty name")
        conf = getattr(skill, "confidence", 0.0)
        if not (0.0 <= conf <= 1.0):
            res.add_error("Confidence out of range")

    return res


def validate_projection_config(config: Dict[str, Any]) -> ValidationResult:
    """
    Validates the structure and attributes of a projection config.
    """
    res = ValidationResult()

    if config is None or not isinstance(config, dict):
        res.add_error("Invalid config format")
        return res

    # fields check
    if "fields" not in config:
        res.add_error("Config missing 'fields' parameter")
    else:
        fields = config["fields"]
        if not isinstance(fields, list):
            res.add_error("'fields' must be a list")
        else:
            for idx, field in enumerate(fields):
                if not isinstance(field, dict):
                    res.add_error(f"Field at index {idx} must be a dictionary")
                    continue
                if "path" not in field:
                    res.add_error(f"Field at index {idx} missing 'path'")
                if "from" not in field:
                    res.add_error(f"Field at index {idx} missing 'from'")
                else:
                    # Validate 'from' path syntax (Fix 6)
                    from_path = field.get("from", "")
                    for part in from_path.split("."):
                        if part and not PATH_PART_RE.match(part):
                            res.add_error(
                                f"Field at index {idx} has invalid 'from' path segment: '{part}'"
                            )

    # include_confidence
    if "include_confidence" in config:
        if not isinstance(config["include_confidence"], bool):
            res.add_error("'include_confidence' must be a boolean")

    # include_provenance
    if "include_provenance" in config:
        if not isinstance(config["include_provenance"], bool):
            res.add_error("'include_provenance' must be a boolean")

    # on_missing
    if "on_missing" in config:
        val = str(config["on_missing"]).lower().strip()
        if val not in ["null", "omit", "error"]:
            res.add_error(f"Invalid 'on_missing' policy value: {config['on_missing']}")

    return res


def validate_output(output: Any) -> ValidationResult:
    """
    Verifies that the projected output is a JSON-serialisable dictionary.
    """
    res = ValidationResult()

    if output is None:
        res.add_error("Output is empty")
        return res

    if not isinstance(output, dict):
        res.add_error("Output must be a dictionary")
        return res

    try:
        json.dumps(output)
    except (TypeError, OverflowError) as e:
        res.add_error(f"Output contains non-serializable objects: {e}")

    return res
