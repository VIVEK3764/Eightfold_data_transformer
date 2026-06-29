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
from src.projection.projection_engine import project
from src.validation.validator import validate_candidate, validate_projection_config, validate_output

def test_pipeline_integration_flow():
    """
    Part 2: End-to-End Integration Test.
    Runs the complete pipeline flow and verifies that no exceptions are raised,
    validations succeed, and projected output is produced.
    """
    csv_path = "tests/gold/recruiter.csv"
    ats_path = "tests/gold/ats.json"
    resume_path = "tests/gold/resume.docx"
    notes_path = "tests/gold/notes.txt"
    
    # 1. Extraction (Adapters)
    profiles = []
    profiles.extend(parse_csv(csv_path))
    profiles.extend(parse_ats(ats_path))
    profiles.extend(parse_resume(resume_path))
    profiles.extend(parse_notes(notes_path))
    assert len(profiles) == 4
    
    # 2. Identity Resolution
    groups = group_records(profiles)
    assert len(groups) == 1
    
    # 3. Merge Engine
    candidate = build_candidate(groups[0])
    
    # 4. Confidence Engine
    candidate = calculate_candidate_confidence(candidate, groups[0])
    
    # 5. Provenance Engine
    candidate = build_candidate_provenance(candidate, groups[0])
    
    # 6. Candidate Validation
    val_res = validate_candidate(candidate)
    assert val_res.valid is True
    assert len(res_errors := val_res.errors) == 0
    
    # 7. Projection Config & Validation
    config = {
        "fields": [
            {"path": "candidate_name", "from": "full_name"},
            {"path": "primary_email", "from": "emails[0]"},
            {"path": "primary_phone", "from": "phones[0]"},
            {"path": "skills_list", "from": "skills[].name"}
        ],
        "include_confidence": True,
        "include_provenance": True,
        "on_missing": "null"
    }
    config_val = validate_projection_config(config)
    assert config_val.valid is True
    
    # 8. Projection Engine
    projected = project(candidate, config)
    assert projected["candidate_name"] == "John Andrew Doe"
    assert projected["primary_email"] == "john@gmail.com"
    assert projected["primary_phone"] == "+919876543210"
    assert projected["skills_list"] == ["Java", "Spring Boot", "AWS"]
    assert projected["overall_confidence"] == 0.912
    assert "provenance" in projected
    
    # 9. Output Validation
    out_val = validate_output(projected)
    assert out_val.valid is True
    
if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
