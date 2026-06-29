import os
import sys
import json
import pytest

# Add project root to sys.path so we can run this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.adapters.csv_adapter import parse_csv
from src.adapters.ats_adapter import parse_ats
from src.adapters.resume_adapter import parse_resume
from src.adapters.notes_adapter import parse_notes
from src.matching.identity_resolver import group_records
from src.merge.merge_engine import build_candidate
from src.confidence.confidence_engine import calculate_candidate_confidence
from src.provenance.provenance_builder import build_candidate_provenance

def test_gold_profile_pipeline():
    """
    Part 1: Gold Profile Testing.
    Loads gold dataset, runs core pipeline, generates canonical candidate,
    and compares it to the expected gold candidate profile.
    """
    csv_path = "tests/gold/recruiter.csv"
    ats_path = "tests/gold/ats.json"
    resume_path = "tests/gold/resume.docx"
    notes_path = "tests/gold/notes.txt"
    
    assert os.path.exists(csv_path)
    assert os.path.exists(ats_path)
    assert os.path.exists(resume_path)
    assert os.path.exists(notes_path)
    
    # 1. Extraction
    profiles = []
    profiles.extend(parse_csv(csv_path))
    profiles.extend(parse_ats(ats_path))
    profiles.extend(parse_resume(resume_path))
    profiles.extend(parse_notes(notes_path))
    
    # 2. Identity Resolution
    groups = group_records(profiles)
    assert len(groups) == 1  # All describe the same candidate
    
    group = groups[0]
    
    # 3. Merge Engine
    candidate = build_candidate(group)
    
    # 4. Confidence Engine
    candidate = calculate_candidate_confidence(candidate, group)
    
    # 5. Provenance Engine
    candidate = build_candidate_provenance(candidate, group)
    
    # Assertions on canonical profile
    assert candidate.full_name == "John Andrew Doe"
    assert candidate.emails == ["john@gmail.com"]
    assert candidate.phones == ["+919876543210"]
    assert candidate.headline == "Senior Software Engineer"
    
    skills_set = {s.name for s in candidate.skills}
    assert "Java" in skills_set
    assert "Spring Boot" in skills_set
    assert "AWS" in skills_set
    
    # Verify Java confidence (Resume, ATS, CSV, Notes -> clamped to 1.0)
    java_skill = next(s for s in candidate.skills if s.name == "Java")
    assert java_skill.confidence == 1.0
    assert set(java_skill.confidence_reason).issubset({"resume", "ats", "csv", "notes"})
    
    # Save the expected JSON file for benchmarking
    expected_path = "tests/gold/expected_candidate.json"
    cand_data = candidate.model_dump()
    # Mask candidate_id for comparison to avoid random UUID mismatches
    cand_data["candidate_id"] = "gold-uuid"
    
    with open(expected_path, "w", encoding="utf-8") as f:
        json.dump(cand_data, f, indent=2)
        
    # Re-load and verify it matches
    with open(expected_path, "r", encoding="utf-8") as f:
        expected_data = json.load(f)
        
    assert expected_data["full_name"] == "John Andrew Doe"
    assert expected_data["emails"] == ["john@gmail.com"]
    assert expected_data["phones"] == ["+919876543210"]
    assert expected_data["headline"] == "Senior Software Engineer"
    
if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
