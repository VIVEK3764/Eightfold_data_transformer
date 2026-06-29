import os
import sys
import pytest

# Add project root to sys.path so we can run this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.matching.identity_resolver import compare_records, group_records

def test_email_match():
    """
    Test 1: Email Match. Expected: matched = True
    """
    record_a = {"emails": ["john.doe@gmail.com"], "phones": [], "full_name": "John Doe"}
    record_b = {"emails": ["john.doe@gmail.com"], "phones": ["+12345"], "full_name": "J. Doe"}
    
    res = compare_records(record_a, record_b)
    assert res.matched is True
    assert res.score == 100.0
    assert res.reason == "email_exact_match"

def test_phone_match():
    """
    Test 2: Phone Match. Expected: matched = True
    """
    record_a = {"emails": ["john@gmail.com"], "phones": ["+919876543210"], "full_name": "John Doe"}
    record_b = {"emails": ["doe@gmail.com"], "phones": ["+919876543210"], "full_name": "J. Doe"}
    
    res = compare_records(record_a, record_b)
    assert res.matched is True
    assert res.score == 90.0
    assert res.reason == "phone_exact_match"

def test_name_company_match():
    """
    Test 3: Name + Company Match. Expected: matched = True
    """
    record_a = {"emails": [], "phones": [], "full_name": "John Doe", "current_company": "Google"}
    record_b = {"emails": [], "phones": [], "full_name": "John A. Doe", "current_company": "Google LLC"}
    
    res = compare_records(record_a, record_b)
    assert res.matched is True
    assert res.score > 90.0
    assert res.reason == "name_company_match"

def test_different_candidates():
    """
    Test 4: Different Candidates. Expected: matched = False
    """
    record_a = {"emails": ["john@gmail.com"], "phones": [], "full_name": "John Doe", "current_company": "Google"}
    record_b = {"emails": ["jane@gmail.com"], "phones": [], "full_name": "Jane Smith", "current_company": "Google"}
    
    res = compare_records(record_a, record_b)
    assert res.matched is False
    assert res.reason == "no_match"

def test_missing_email_fallback():
    """
    Test 5: Missing Email. Fallback logic works.
    Falls back to phone matching first. If phone missing/different, falls back to name + company.
    """
    # Fallback to Phone Match
    record_a = {"emails": [], "phones": ["+919876543210"], "full_name": "John Doe"}
    record_b = {"emails": ["other@gmail.com"], "phones": ["+919876543210"], "full_name": "Jane Doe"}
    res1 = compare_records(record_a, record_b)
    assert res1.matched is True
    assert res1.reason == "phone_exact_match"
    
    # Fallback to Name + Company Match (when phone also missing/different)
    record_c = {"emails": [], "phones": [], "full_name": "John Doe", "current_company": "Google"}
    record_d = {"emails": [], "phones": ["+11111"], "full_name": "John A Doe", "current_company": "Google"}
    res2 = compare_records(record_c, record_d)
    assert res2.matched is True
    assert res2.reason == "name_company_match"

def test_grouping_same_candidate():
    """
    Test 6: Grouping. Input: CSV + ATS + Resume (same candidate). Output: 1 group.
    """
    csv = {"emails": ["john@gmail.com"], "phones": [], "full_name": "John Doe", "current_company": "Google"}
    ats = {"emails": [], "phones": ["+919876543210"], "full_name": "J. Doe", "current_company": "Google"}
    resume = {"emails": ["john@gmail.com"], "phones": ["+919876543210"], "full_name": "John A Doe", "current_company": "Google"}
    
    groups = group_records([csv, ats, resume])
    assert len(groups) == 1
    assert len(groups[0]) == 3

def test_grouping_multiple_candidates():
    """
    Test 7: Multiple Candidates. Input: records for two people. Output: 2 groups.
    """
    cand1_csv = {"emails": ["john@gmail.com"], "phones": [], "full_name": "John Doe"}
    cand1_ats = {"emails": ["john@gmail.com"], "phones": [], "full_name": "J. Doe"}
    
    cand2_resume = {"emails": ["jane@gmail.com"], "phones": [], "full_name": "Jane Smith"}
    cand2_notes = {"emails": [], "phones": [], "full_name": "Jane Smith", "current_company": "Microsoft"}
    
    groups = group_records([cand1_csv, cand2_resume, cand1_ats, cand2_notes])
    assert len(groups) == 2
    
    # Confirm sizes of groups
    g1 = next(g for g in groups if cand1_csv in g)
    g2 = next(g for g in groups if cand2_resume in g)
    assert len(g1) == 2
    assert len(g2) == 2

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
