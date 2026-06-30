"""
Tests for the improvements introduced during the architecture review:
  - Fix 1: Shared constants are used consistently
  - Fix 2: Phone digit-strip matching in identity resolution
  - Fix 3: Experience dedup with company-name variants
  - Fix 4: Name confidence fuzzy comparison (variants treated as agreements)
  - Fix 5: Provenance pre-sort efficiency (correctness check)
  - Fix 6: Validation new checks (full_name missing, negative years_exp, empty skill)
  - Fix 8: Expanded SKILL_MAP coverage
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config.constants import SOURCE_PRIORITY, SOURCE_RELIABILITY
from src.matching.identity_resolver import compare_records, group_records
from src.merge.merge_engine import build_candidate, merge_experience
from src.confidence.confidence_engine import calculate_name_confidence
from src.normalizers.skills import normalize_skill
from src.models.candidate import Candidate, Skill
from src.validation.validator import validate_candidate, validate_projection_config


# ─── Fix 1: Shared constants ─────────────────────────────────────────────────

def test_shared_constants_source_priority():
    """Constants module exposes SOURCE_PRIORITY and SOURCE_RELIABILITY."""
    assert SOURCE_PRIORITY["resume"] < SOURCE_PRIORITY["ats"]
    assert SOURCE_PRIORITY["ats"] < SOURCE_PRIORITY["csv"]
    assert SOURCE_RELIABILITY["resume"] > SOURCE_RELIABILITY["notes"]


# ─── Fix 2: Phone digit-strip matching ───────────────────────────────────────

def test_phone_formatted_variants_match():
    """
    '+1 234 567 8900' and '+12345678900' are the same number formatted differently.
    Identity resolver must match them via digit-strip comparison.
    """
    rec_a = {"source": "csv", "full_name": "Alice", "emails": [], "phones": ["+1 234 567 8900"]}
    rec_b = {"source": "ats", "full_name": "Alice", "emails": [], "phones": ["+12345678900"]}
    result = compare_records(rec_a, rec_b)
    assert result.matched is True
    assert result.reason == "phone_exact_match"


def test_phone_hyphen_space_match():
    """'+1-234-567-8900' and '+1 234 567 8900' must match."""
    rec_a = {"source": "csv", "phones": ["+1-234-567-8900"]}
    rec_b = {"source": "ats", "phones": ["+1 234 567 8900"]}
    result = compare_records(rec_a, rec_b)
    assert result.matched is True


def test_different_phones_do_not_match():
    """Genuinely different phone numbers must not match."""
    rec_a = {"source": "csv", "phones": ["+919876543210"]}
    rec_b = {"source": "ats", "phones": ["+919876543211"]}
    result = compare_records(rec_a, rec_b)
    assert result.matched is False


# ─── Fix 3: Experience dedup with company-name variants ──────────────────────

def test_experience_dedup_company_variants():
    """
    'Google' and 'Google LLC' describe the same employer.
    Merge engine must not produce duplicate experience entries.
    """
    rec_resume = {
        "source": "resume",
        "experience": [{"company": "Google", "title": "SDE", "start": "2020-01", "end": "Present"}],
    }
    rec_ats = {
        "source": "ats",
        "experience": [{"company": "Google LLC", "title": "SDE", "start": "2020-01", "end": "Present"}],
    }
    cand = build_candidate([rec_resume, rec_ats])
    assert len(cand.experience) == 1


def test_experience_dedup_inc_suffix():
    """'Stripe Inc' and 'Stripe' must deduplicate."""
    records = [
        {"source": "resume", "experience": [{"company": "Stripe", "title": "Eng"}]},
        {"source": "csv",    "experience": [{"company": "Stripe Inc", "title": "Eng"}]},
    ]
    cand = build_candidate(records)
    assert len(cand.experience) == 1


def test_experience_different_companies_kept():
    """Genuinely different companies should both appear."""
    records = [
        {"source": "resume", "experience": [{"company": "Google", "title": "Eng"}]},
        {"source": "ats",    "experience": [{"company": "Microsoft", "title": "PM"}]},
    ]
    cand = build_candidate(records)
    assert len(cand.experience) == 2


# ─── Fix 4: Name confidence with fuzzy variants ──────────────────────────────

def test_name_variants_do_not_penalise_confidence():
    """
    'John Andrew Doe' (resume winner) vs 'John Doe' (CSV variant).
    These are near-variants, not adversarial mismatches — confidence must NOT be penalised.
    The old code produced 0.95 - 0.10 = 0.85; the new code produces ≥ 0.95.
    """
    records = [
        {"source": "resume", "full_name": "John Andrew Doe"},
        {"source": "csv",    "full_name": "John Doe"},
    ]
    conf = calculate_name_confidence("John Andrew Doe", records)
    assert conf >= 0.95, f"Expected >= 0.95, got {conf}"


def test_genuinely_different_name_penalises():
    """
    'Alice Smith' vs 'Bob Jones' are genuinely different names.
    The confidence for the winning name should be penalised.
    """
    records = [
        {"source": "resume", "full_name": "Alice Smith"},
        {"source": "ats",    "full_name": "Bob Jones"},
    ]
    conf = calculate_name_confidence("Alice Smith", records)
    assert conf < 0.95, f"Expected < 0.95 due to conflict, got {conf}"


# ─── Fix 6: Validation enhancements ─────────────────────────────────────────

def test_validation_missing_full_name():
    """Candidate without full_name must produce a validation error."""
    cand = Candidate(candidate_id="uuid-1")  # full_name defaults to None
    res = validate_candidate(cand)
    assert res.valid is False
    assert any("full_name" in err for err in res.errors)


def test_validation_negative_years_experience():
    """Negative years_experience must fail validation."""
    cand = Candidate(candidate_id="uuid-1", full_name="Test User", years_experience=-3)
    res = validate_candidate(cand)
    assert res.valid is False
    assert any("years_experience" in err for err in res.errors)


def test_validation_empty_skill_name():
    """A skill with an empty name must fail validation."""
    skill = Skill(name="", confidence=0.9)
    cand = Candidate(candidate_id="uuid-1", full_name="Test User", skills=[skill])
    res = validate_candidate(cand)
    assert res.valid is False
    assert any("empty name" in err for err in res.errors)


def test_validation_config_invalid_from_path():
    """A config field with an invalid 'from' path syntax must fail."""
    config = {
        "fields": [{"path": "out", "from": "emails[abc]"}],  # invalid bracket index
        "on_missing": "null",
    }
    res = validate_projection_config(config)
    assert res.valid is False


def test_validation_config_valid_paths():
    """Valid 'from' path expressions must not produce errors."""
    config = {
        "fields": [
            {"path": "name", "from": "full_name"},
            {"path": "email", "from": "emails[0]"},
            {"path": "skills", "from": "skills[].name"},
        ],
        "on_missing": "null",
    }
    res = validate_projection_config(config)
    assert res.valid is True


# ─── Fix 8: Expanded SKILL_MAP ───────────────────────────────────────────────

@pytest.mark.parametrize("raw, expected", [
    ("typescript", "TypeScript"),
    ("ts", "TypeScript"),
    ("react", "React"),
    ("reactjs", "React"),
    ("golang", "Go"),
    ("go", "Go"),
    ("kubernetes", "Kubernetes"),
    ("k8s", "Kubernetes"),
    ("postgresql", "PostgreSQL"),
    ("postgres", "PostgreSQL"),
    ("aws", "AWS"),
    ("amazon web services", "AWS"),
    ("gcp", "GCP"),
    ("ml", "Machine Learning"),
    ("python", "Python"),
    ("java", "Java"),
])
def test_extended_skill_map(raw, expected):
    """Extended SKILL_MAP maps new aliases to canonical skill names."""
    assert normalize_skill(raw) == expected


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
