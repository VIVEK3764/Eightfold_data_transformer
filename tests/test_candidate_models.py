import os
import sys
import json
import pytest

# Add project root to sys.path so we can run this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.candidate import Candidate, Skill, Experience, Education, Provenance

def test_skill_creation():
    """
    Test 1: Skill creation. Verify fields are stored correctly.
    """
    skill = Skill(name="Java", confidence=1.0, confidence_reason=["resume", "ats"])
    assert skill.name == "Java"
    assert skill.confidence == 1.0
    assert skill.confidence_reason == ["resume", "ats"]
    
    # Verify defaults
    default_skill = Skill(name="Python")
    assert default_skill.name == "Python"
    assert default_skill.confidence == 0.0
    assert default_skill.confidence_reason == []

def test_experience_creation():
    """
    Test 2: Experience creation. Verify serialization works.
    """
    exp = Experience(
        company="Google",
        title="Software Engineer",
        start="2021-06",
        end=None,
        summary="Backend development"
    )
    assert exp.company == "Google"
    assert exp.title == "Software Engineer"
    assert exp.start == "2021-06"
    assert exp.end is None
    assert exp.summary == "Backend development"
    
    # Verify serialization
    dumped = exp.model_dump()
    assert dumped["company"] == "Google"
    assert dumped["title"] == "Software Engineer"
    assert dumped["start"] == "2021-06"
    assert dumped["end"] is None
    assert dumped["summary"] == "Backend development"
    
    # JSON serialization
    serialized = exp.model_dump_json()
    parsed = json.loads(serialized)
    assert parsed["company"] == "Google"

def test_education_creation():
    """
    Test 3: Education creation. Verify optional fields behave correctly.
    """
    edu = Education(institution="IIT Patna")
    assert edu.institution == "IIT Patna"
    assert edu.degree is None
    assert edu.field is None
    assert edu.end_year is None

    # Full creation
    edu_full = Education(
        institution="Stanford University",
        degree="M.S.",
        field="Computer Science",
        end_year=2024
    )
    assert edu_full.institution == "Stanford University"
    assert edu_full.degree == "M.S."
    assert edu_full.field == "Computer Science"
    assert edu_full.end_year == 2024

def test_provenance_creation():
    """
    Test 4: Provenance creation. Verify default values work.
    """
    prov = Provenance(
        field="skill",
        value="Java",
        source="resume.pdf",
        method="skills_section_extraction"
    )
    assert prov.field == "skill"
    assert prov.value == "Java"
    assert prov.source == "resume.pdf"
    assert prov.method == "skills_section_extraction"
    assert prov.source_confidence == 0.0

def test_candidate_creation():
    """
    Test 5: Candidate creation. Instantiate a complete candidate.
    Verify nested models, serialization, model_dump(), and JSON conversion.
    """
    skill = Skill(name="Java", confidence=1.0, confidence_reason=["resume"])
    exp = Experience(company="Google", title="Software Engineer", start="2021-06", summary="Backend")
    edu = Education(institution="IIT Patna", degree="B.Tech", field="CS", end_year=2027)
    prov = Provenance(field="skill", value="Java", source="resume.pdf", method="regex")
    
    cand = Candidate(
        candidate_id="uuid-1234",
        full_name="John Doe",
        emails=["john.doe@gmail.com"],
        phones=["+12345678900"],
        location={"city": "San Francisco", "country": "US"},
        links={"linkedin": "linkedin.com/in/johndoe"},
        headline="Senior Backend Engineer",
        years_experience=5,
        skills=[skill],
        experience=[exp],
        education=[edu],
        provenance=[prov],
        overall_confidence=0.95
    )
    
    assert cand.candidate_id == "uuid-1234"
    assert cand.full_name == "John Doe"
    assert cand.emails == ["john.doe@gmail.com"]
    assert cand.phones == ["+12345678900"]
    assert cand.location == {"city": "San Francisco", "country": "US"}
    assert cand.links == {"linkedin": "linkedin.com/in/johndoe"}
    assert cand.headline == "Senior Backend Engineer"
    assert cand.years_experience == 5
    assert len(cand.skills) == 1
    assert cand.skills[0].name == "Java"
    assert len(cand.experience) == 1
    assert cand.experience[0].company == "Google"
    assert len(cand.education) == 1
    assert cand.education[0].institution == "IIT Patna"
    assert len(cand.provenance) == 1
    assert cand.provenance[0].field == "skill"
    assert cand.overall_confidence == 0.95
    
    # model_dump succeeds
    dumped = cand.model_dump()
    assert isinstance(dumped, dict)
    assert dumped["candidate_id"] == "uuid-1234"
    assert dumped["skills"][0]["name"] == "Java"
    assert dumped["experience"][0]["company"] == "Google"
    
    # JSON serialization succeeds
    json_str = cand.model_dump_json()
    assert isinstance(json_str, str)
    parsed = json.loads(json_str)
    assert parsed["candidate_id"] == "uuid-1234"
    assert parsed["location"]["city"] == "San Francisco"

def test_candidate_defaults():
    """
    Test 6: Candidate defaults. Create empty candidate. Verify list and dict initialization
    and verify no shared mutable state exists.
    """
    cand1 = Candidate(candidate_id="id-1")
    cand2 = Candidate(candidate_id="id-2")
    
    # Verify lists and dicts are initialized correctly
    assert cand1.emails == []
    assert cand1.phones == []
    assert cand1.location == {}
    assert cand1.links == {}
    assert cand1.skills == []
    assert cand1.experience == []
    assert cand1.education == []
    assert cand1.provenance == []
    assert cand1.overall_confidence == 0.0
    
    # Verify no shared mutable state
    cand1.emails.append("test@example.com")
    cand1.location["city"] = "San Francisco"
    
    assert cand2.emails == []
    assert cand2.location == {}

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
