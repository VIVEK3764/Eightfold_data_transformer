import os
import sys
import pytest

# Add project root to sys.path so we can run this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.candidate import Candidate, Skill
from src.validation.validator import (
    validate_candidate,
    validate_projection_config,
    validate_output
)

# Dummy non-serializable class
class DummyObject:
    pass

@pytest.fixture
def valid_candidate():
    skill = Skill(name="Java", confidence=0.90)
    return Candidate(
        candidate_id="uuid-1",
        full_name="John Doe",
        emails=["john@gmail.com"],
        phones=["+919876543210"],
        skills=[skill],
        overall_confidence=0.92
    )

def test_valid_candidate(valid_candidate):
    """
    Test 1: Valid Candidate. Expected: valid = True.
    """
    res = validate_candidate(valid_candidate)
    assert res.valid is True
    assert len(res.errors) == 0

def test_invalid_email(valid_candidate):
    """
    Test 2: Invalid Email. Expected: validation failure.
    """
    valid_candidate.emails.append("invalid_email")
    res = validate_candidate(valid_candidate)
    assert res.valid is False
    assert any("Invalid email" in err for err in res.errors)

def test_invalid_phone(valid_candidate):
    """
    Test 3: Invalid Phone. Expected: validation failure.
    """
    valid_candidate.phones.append("123abc")
    res = validate_candidate(valid_candidate)
    assert res.valid is False
    assert any("Invalid phone" in err for err in res.errors)

def test_invalid_confidence(valid_candidate):
    """
    Test 4: Invalid Confidence. Expected: validation failure.
    """
    valid_candidate.overall_confidence = 1.5
    res = validate_candidate(valid_candidate)
    assert res.valid is False
    assert any("Confidence out of range" in err for err in res.errors)

def test_valid_projection_config():
    """
    Test 5: Valid Projection Config. Expected: valid = True.
    """
    config = {
        "fields": [
            {"path": "candidate_name", "from": "full_name"},
            {"path": "primary_email", "from": "emails[0]"}
        ],
        "include_confidence": True,
        "include_provenance": False,
        "on_missing": "null"
    }
    res = validate_projection_config(config)
    assert res.valid is True

def test_invalid_projection_config():
    """
    Test 6: Invalid Projection Config. Expected: validation failure.
    """
    config_missing_fields = {
        "on_missing": "invalid_value"
    }
    res = validate_projection_config(config_missing_fields)
    assert res.valid is False
    assert any("Config missing 'fields'" in err for err in res.errors)
    assert any("Invalid 'on_missing' policy" in err for err in res.errors)

def test_valid_output():
    """
    Test 7: Valid Output. Expected: valid = True.
    """
    output = {
        "name": "John Doe",
        "skills": ["Java", "Python"],
        "confidence": 0.95
    }
    res = validate_output(output)
    assert res.valid is True

def test_invalid_output():
    """
    Test 8: Invalid Output. Expected: validation failure.
    """
    output = {
        "name": "John Doe",
        "custom_object": DummyObject()  # Non-serializable
    }
    res = validate_output(output)
    assert res.valid is False
    assert any("Output contains non-serializable objects" in err for err in res.errors)

def test_multiple_errors(valid_candidate):
    """
    Test 9: Multiple Errors. Verify all errors reported.
    """
    valid_candidate.emails.append("abc")
    valid_candidate.phones.append("123abc")
    valid_candidate.overall_confidence = 2.0
    
    res = validate_candidate(valid_candidate)
    assert res.valid is False
    assert len(res.errors) == 3
    assert any("Invalid email" in err for err in res.errors)
    assert any("Invalid phone" in err for err in res.errors)
    assert any("Confidence out of range" in err for err in res.errors)

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
