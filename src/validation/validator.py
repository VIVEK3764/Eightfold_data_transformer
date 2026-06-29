import re
import json
from typing import Any, Dict
from src.models.candidate import Candidate
from src.validation.validation_result import ValidationResult

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
PHONE_E164_REGEX = re.compile(r"^\+[1-9]\d{1,14}$")

def validate_candidate(candidate: Any) -> ValidationResult:
    """
    Validates a Candidate object for correct structure, valid formats, and bounds.
    """
    res = ValidationResult()
    
    if candidate is None:
        res.add_error("Candidate object is missing")
        return res
        
    # Check Candidate ID
    cand_id = getattr(candidate, "candidate_id", None)
    if not cand_id:
        res.add_error("Candidate missing candidate_id")
        
    # Validate emails
    emails = getattr(candidate, "emails", []) or []
    for email in emails:
        if not EMAIL_REGEX.match(email):
            res.add_error(f"Invalid email: {email}")
            
    # Validate phones
    phones = getattr(candidate, "phones", []) or []
    for phone in phones:
        if not PHONE_E164_REGEX.match(phone):
            res.add_error(f"Invalid phone: {phone}")
            
    # Validate overall candidate confidence
    overall_conf = getattr(candidate, "overall_confidence", 0.0)
    if not (0.0 <= overall_conf <= 1.0):
        res.add_error("Confidence out of range")
        
    # Validate skill confidences
    skills = getattr(candidate, "skills", []) or []
    for skill in skills:
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
        
    # 1. fields check
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
                    
    # 2. include_confidence check
    if "include_confidence" in config:
        if not isinstance(config["include_confidence"], bool):
            res.add_error("'include_confidence' must be a boolean")
            
    # 3. include_provenance check
    if "include_provenance" in config:
        if not isinstance(config["include_provenance"], bool):
            res.add_error("'include_provenance' must be a boolean")
            
    # 4. on_missing check
    if "on_missing" in config:
        val = str(config["on_missing"]).lower().strip()
        if val not in ["null", "omit", "error"]:
            res.add_error(f"Invalid 'on_missing' policy value: {config['on_missing']}")
            
    return res

def validate_output(output: Any) -> ValidationResult:
    """
    Verifies that the projected output is JSON-serializable and structured correctly.
    """
    res = ValidationResult()
    
    if output is None:
        res.add_error("Output is empty")
        return res
        
    if not isinstance(output, dict):
        res.add_error("Output must be a dictionary")
        return res
        
    # Check JSON serializability
    try:
        json.dumps(output)
    except (TypeError, OverflowError) as e:
        res.add_error(f"Output contains non-serializable objects: {e}")
        
    return res
