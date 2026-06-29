import os
import sys
import pytest

# Add project root to sys.path so we can run this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.candidate import Candidate, Skill, Provenance
from src.projection.projection_engine import project, ProjectionError

@pytest.fixture
def sample_candidate():
    skill1 = Skill(name="Java", confidence=1.0)
    skill2 = Skill(name="Spring Boot", confidence=0.95)
    prov = Provenance(
        field="full_name",
        value="John Doe",
        source="resume",
        method="extraction",
        source_confidence=0.95
    )
    return Candidate(
        candidate_id="uuid-1",
        full_name="John Doe",
        emails=["john@gmail.com", "john.work@gmail.com"],
        phones=["+919876543210"],
        skills=[skill1, skill2],
        provenance=[prov],
        overall_confidence=0.92
    )

def test_field_rename(sample_candidate):
    """
    Test 1: Field Rename (full_name -> candidate_name).
    """
    config = {
        "fields": [
            {"path": "candidate_name", "from": "full_name"}
        ]
    }
    output = project(sample_candidate, config)
    assert output == {"candidate_name": "John Doe"}

def test_primary_email(sample_candidate):
    """
    Test 2: Primary Email (emails[0]).
    """
    config = {
        "fields": [
            {"path": "primary_email", "from": "emails[0]"}
        ]
    }
    output = project(sample_candidate, config)
    assert output == {"primary_email": "john@gmail.com"}

def test_skills_projection(sample_candidate):
    """
    Test 3: Skills Projection (skills[].name).
    """
    config = {
        "fields": [
            {"path": "skills", "from": "skills[].name"}
        ]
    }
    output = project(sample_candidate, config)
    assert output == {"skills": ["Java", "Spring Boot"]}

def test_confidence_toggle(sample_candidate):
    """
    Test 4: Confidence Toggle (include_confidence = True / False).
    """
    config_enabled = {"fields": [], "include_confidence": True}
    config_disabled = {"fields": [], "include_confidence": False}
    
    assert project(sample_candidate, config_enabled) == {"overall_confidence": 0.92}
    assert project(sample_candidate, config_disabled) == {}

def test_provenance_toggle(sample_candidate):
    """
    Test 5: Provenance Toggle (include_provenance = True / False).
    """
    config_enabled = {"fields": [], "include_provenance": True}
    config_disabled = {"fields": [], "include_provenance": False}
    
    out = project(sample_candidate, config_enabled)
    assert "provenance" in out
    assert out["provenance"][0]["value"] == "John Doe"
    
    assert project(sample_candidate, config_disabled) == {}

def test_null_policy(sample_candidate):
    """
    Test 6: Null Policy. Missing field becomes null.
    """
    config = {
        "fields": [
            {"path": "missing_field", "from": "nonexistent_path"}
        ],
        "on_missing": "null"
    }
    output = project(sample_candidate, config)
    assert output == {"missing_field": None}

def test_omit_policy(sample_candidate):
    """
    Test 7: Omit Policy. Missing field removed from output.
    """
    config = {
        "fields": [
            {"path": "name", "from": "full_name"},
            {"path": "missing_field", "from": "nonexistent_path"}
        ],
        "on_missing": "omit"
    }
    output = project(sample_candidate, config)
    assert output == {"name": "John Doe"}

def test_error_policy(sample_candidate):
    """
    Test 8: Error Policy. Structured exception raised.
    """
    config = {
        "fields": [
            {"path": "missing_field", "from": "nonexistent_path"}
        ],
        "on_missing": "error"
    }
    with pytest.raises(ProjectionError):
        project(sample_candidate, config)

def test_empty_candidate():
    """
    Test 9: Empty Candidate. No crashes.
    """
    cand = Candidate(candidate_id="uuid-empty")
    config = {
        "fields": [
            {"path": "name", "from": "full_name"}
        ],
        "on_missing": "null"
    }
    output = project(cand, config)
    assert output == {"name": None}

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
