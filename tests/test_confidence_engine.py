import os
import sys
import pytest

# Add project root to sys.path so we can run this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.candidate import Candidate, Skill
from src.confidence.confidence_engine import (
    calculate_candidate_confidence,
    calculate_skill_confidence,
    calculate_name_confidence
)

def test_single_source_skill():
    """
    Test 1: Single Source Skill (Resume only -> 0.95).
    """
    records = [
        {"source": "resume", "skills": ["Java"]}
    ]
    conf, sources = calculate_skill_confidence("Java", records)
    assert conf == 0.95
    assert sources == ["resume"]

def test_resume_ats_agreement():
    """
    Test 2: Resume + ATS Agreement (0.95 base + 0.05 agreement = 1.0).
    """
    records = [
        {"source": "resume", "skills": ["Java"]},
        {"source": "ats", "skills": ["Java"]}
    ]
    conf, sources = calculate_skill_confidence("Java", records)
    assert conf == 1.0
    assert set(sources) == {"resume", "ats"}

def test_notes_only_skill():
    """
    Test 3: Notes Only Skill (Notes -> 0.60).
    """
    records = [
        {"source": "notes", "skills": ["AWS"]}
    ]
    conf, sources = calculate_skill_confidence("AWS", records)
    assert conf == 0.60
    assert sources == ["notes"]

def test_conflict_penalty():
    """
    Test 4: Conflict Penalty (Resume has "John Andrew Doe", CSV has "John Doe" -> 0.95 - 0.10 = 0.85).
    """
    records = [
        {"source": "resume", "full_name": "John Andrew Doe"},
        {"source": "csv", "full_name": "John Doe"}
    ]
    conf = calculate_name_confidence("John Andrew Doe", records)
    assert conf == 0.85

def test_clamp_confidence():
    """
    Test 5: Clamp. Confidence never exceeds 1.0.
    """
    records = [
        {"source": "resume", "skills": ["Java"]},
        {"source": "ats", "skills": ["Java"]},
        {"source": "csv", "skills": ["Java"]},
        {"source": "notes", "skills": ["Java"]}
    ]
    # base 0.95 + 3 * 0.05 = 1.10 clamped to 1.00
    conf, sources = calculate_skill_confidence("Java", records)
    assert conf == 1.00
    assert len(sources) == 4

def test_candidate_overall_confidence():
    """
    Test 6: Candidate Confidence. Overall confidence calculated (average of fields).
    """
    skill = Skill(name="Java", confidence=0.0)
    cand = Candidate(
        candidate_id="uuid-1",
        full_name="John Doe",
        emails=["john@gmail.com"],
        phones=[],
        skills=[skill]
    )
    
    records = [
        {"source": "resume", "full_name": "John Doe", "emails": ["john@gmail.com"], "skills": ["Java"]}
    ]
    
    updated_cand = calculate_candidate_confidence(cand, records)
    
    # name conf = 0.95 (resume only)
    # email conf = 0.95 (resume only)
    # skill conf = 0.95 (resume only)
    # phone is empty -> excluded from score
    # overall = (0.95 + 0.95 + 0.95) / 3 = 0.95
    assert updated_cand.overall_confidence == 0.95

def test_confidence_reasons():
    """
    Test 7: Confidence Reasons. Sources correctly stored in confidence_reason list.
    """
    skill = Skill(name="Java", confidence=0.0)
    cand = Candidate(
        candidate_id="uuid-1",
        skills=[skill]
    )
    
    records = [
        {"source": "resume", "skills": ["Java"]},
        {"source": "ats", "skills": ["Java"]}
    ]
    
    updated_cand = calculate_candidate_confidence(cand, records)
    assert set(updated_cand.skills[0].confidence_reason) == {"resume", "ats"}

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
