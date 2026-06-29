import os
import sys
import pytest

# Add project root to sys.path so we can run this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.candidate import Candidate, Skill, Experience, Education
from src.provenance.provenance_builder import build_candidate_provenance

def test_name_provenance():
    """
    Test 1: Name Provenance. Verify source recorded correctly.
    """
    cand = Candidate(candidate_id="uuid-1", full_name="John Doe")
    records = [{"source": "resume", "full_name": "John Doe"}]
    
    updated_cand = build_candidate_provenance(cand, records)
    assert len(updated_cand.provenance) == 1
    prov = updated_cand.provenance[0]
    assert prov.field == "full_name"
    assert prov.value == "John Doe"
    assert prov.source == "resume"
    assert prov.method == "name_extraction"

def test_email_provenance():
    """
    Test 2: Email Provenance. Verify extraction method.
    """
    cand = Candidate(candidate_id="uuid-1", emails=["john@gmail.com"])
    records = [{"source": "csv", "emails": ["john@gmail.com"]}]
    
    updated_cand = build_candidate_provenance(cand, records)
    assert len(updated_cand.provenance) == 1
    prov = updated_cand.provenance[0]
    assert prov.field == "email"
    assert prov.value == "john@gmail.com"
    assert prov.source == "csv"
    assert prov.method == "direct_mapping"

def test_skill_provenance():
    """
    Test 3: Skill Provenance. Verify each skill has provenance.
    """
    skill1 = Skill(name="Java")
    skill2 = Skill(name="Python")
    cand = Candidate(candidate_id="uuid-1", skills=[skill1, skill2])
    records = [
        {"source": "resume", "skills": ["Java"]},
        {"source": "ats", "skills": ["Python"]}
    ]
    
    updated_cand = build_candidate_provenance(cand, records)
    skill_provs = [p for p in updated_cand.provenance if p.field == "skill"]
    assert len(skill_provs) == 2
    assert {p.value for p in skill_provs} == {"Java", "Python"}
    
    java_prov = next(p for p in skill_provs if p.value == "Java")
    python_prov = next(p for p in skill_provs if p.value == "Python")
    assert java_prov.source == "resume"
    assert python_prov.source == "ats"

def test_conflict_winner_provenance():
    """
    Test 4: Conflict Winner Provenance. Verify winning source and conflict resolution method stored.
    """
    cand = Candidate(candidate_id="uuid-1", full_name="John Andrew Doe")
    records = [
        {"source": "resume", "full_name": "John Andrew Doe"},
        {"source": "csv", "full_name": "John Doe"}
    ]
    
    updated_cand = build_candidate_provenance(cand, records)
    assert len(updated_cand.provenance) == 1
    prov = updated_cand.provenance[0]
    assert prov.field == "full_name"
    assert prov.value == "John Andrew Doe"
    assert prov.source == "resume"
    assert prov.method == "winner_selected_from_conflict"

def test_multiple_provenance_entries():
    """
    Test 5: Multiple Provenance Entries. Verify candidate contains all expected entries.
    """
    skill = Skill(name="Java")
    exp = Experience(company="Google", title="SDE")
    edu = Education(institution="IIT")
    
    cand = Candidate(
        candidate_id="uuid-1",
        full_name="John Doe",
        emails=["john@gmail.com"],
        skills=[skill],
        experience=[exp],
        education=[edu]
    )
    
    records = [
        {"source": "resume", "full_name": "John Doe", "emails": ["john@gmail.com"], "skills": ["Java"],
         "experience": [{"company": "Google", "title": "SDE"}], "education": [{"institution": "IIT"}]}
    ]
    
    updated_cand = build_candidate_provenance(cand, records)
    fields = [p.field for p in updated_cand.provenance]
    assert "full_name" in fields
    assert "email" in fields
    assert "skill" in fields
    assert "experience" in fields
    assert "education" in fields

def test_empty_candidate():
    """
    Test 6: Empty Candidate. No crashes.
    """
    cand = Candidate(candidate_id="uuid-1")
    updated_cand = build_candidate_provenance(cand, [])
    assert updated_cand.provenance == []

def test_source_confidence():
    """
    Test 7: Source Confidence. Verify correct reliability values stored in provenance.
    """
    cand = Candidate(candidate_id="uuid-1", full_name="John Doe")
    records = [{"source": "resume", "full_name": "John Doe"}]
    
    updated_cand = build_candidate_provenance(cand, records)
    prov = updated_cand.provenance[0]
    assert prov.source_confidence == 0.95  # Resume reliability

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
