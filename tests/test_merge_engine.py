import os
import sys
import pytest

# Add project root to sys.path so we can run this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.candidate import Candidate
from src.merge.merge_engine import build_candidate

def test_name_conflict():
    """
    Test 1: Name Conflict. Resume wins over CSV.
    """
    resume_rec = {"source": "resume", "full_name": "John Andrew Doe"}
    csv_rec = {"source": "csv", "full_name": "John Doe"}
    
    cand = build_candidate([csv_rec, resume_rec])
    assert cand.full_name == "John Andrew Doe"

def test_email_merge():
    """
    Test 2: Email Merge. Duplicate emails removed.
    """
    resume_rec = {"source": "resume", "emails": ["john@gmail.com"]}
    csv_rec = {"source": "csv", "emails": ["john@gmail.com", "john.work@gmail.com"]}
    
    cand = build_candidate([resume_rec, csv_rec])
    assert cand.emails == ["john@gmail.com", "john.work@gmail.com"]

def test_phone_merge():
    """
    Test 3: Phone Merge. Duplicate phones removed.
    """
    resume_rec = {"source": "resume", "phones": ["+919876543210"]}
    ats_rec = {"source": "ats", "phones": ["+919876543210"]}
    
    cand = build_candidate([resume_rec, ats_rec])
    assert cand.phones == ["+919876543210"]

def test_skill_merge():
    """
    Test 4: Skill Merge. Unique set of skills merged.
    """
    resume_rec = {"source": "resume", "skills": ["Java", "Spring"]}
    ats_rec = {"source": "ats", "skills": ["Java", "AWS"]}
    
    cand = build_candidate([resume_rec, ats_rec])
    skill_names = [s.name for s in cand.skills]
    assert skill_names == ["Java", "Spring", "AWS"]

def test_experience_merge():
    """
    Test 5: Experience Merge. Duplicates removed.
    """
    resume_rec = {
        "source": "resume",
        "experience": [
            {"company": "Google", "title": "SDE", "start": "2021-06", "end": "Present", "summary": "Backend"}
        ]
    }
    ats_rec = {
        "source": "ats",
        "experience": [
            {"company": "Google", "title": "SDE", "start": "2021-06", "end": "Present", "summary": "Backend"},
            {"company": "Microsoft", "title": "SDE-II", "start": "2019-01", "end": "2021-05", "summary": "Full Stack"}
        ]
    }
    
    cand = build_candidate([resume_rec, ats_rec])
    assert len(cand.experience) == 2
    assert cand.experience[0].company == "Google"
    assert cand.experience[1].company == "Microsoft"

def test_education_merge():
    """
    Test 6: Education Merge. Duplicates removed.
    """
    resume_rec = {
        "source": "resume",
        "education": [
            {"institution": "IIT Patna", "degree": "B.Tech", "field": "CS", "end_year": 2027}
        ]
    }
    ats_rec = {
        "source": "ats",
        "education": [
            {"institution": "IIT Patna", "degree": "B.Tech", "field": "CS", "end_year": 2027}
        ]
    }
    
    cand = build_candidate([resume_rec, ats_rec])
    assert len(cand.education) == 1
    assert cand.education[0].institution == "IIT Patna"

def test_single_source_candidate():
    """
    Test 7: Single Source Candidate. Builds correctly.
    """
    resume_rec = {
        "source": "resume",
        "full_name": "Single Candidate",
        "emails": ["single@gmail.com"],
        "phones": ["+11111"],
        "headline": "Manager",
        "current_company": "Uber",
        "skills": ["Management"]
    }
    
    cand = build_candidate([resume_rec])
    assert cand.full_name == "Single Candidate"
    assert cand.emails == ["single@gmail.com"]
    assert cand.phones == ["+11111"]
    assert cand.headline == "Manager"
    assert [s.name for s in cand.skills] == ["Management"]

def test_empty_fields():
    """
    Test 8: Empty Fields. No crashes.
    """
    empty_rec = {
        "source": "resume",
        "full_name": None,
        "emails": None,
        "phones": None,
        "headline": None,
        "skills": None,
        "experience": None,
        "education": None
    }
    
    cand = build_candidate([empty_rec])
    assert cand.full_name is None
    assert cand.emails == []
    assert cand.phones == []
    assert cand.skills == []
    assert cand.experience == []
    assert cand.education == []

def test_candidate_object_type():
    """
    Test 9: Candidate Object. Verify return type is Candidate model.
    """
    rec = {"source": "resume", "full_name": "Test User"}
    cand = build_candidate([rec])
    
    assert isinstance(cand, Candidate)
    assert cand.candidate_id is not None

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
