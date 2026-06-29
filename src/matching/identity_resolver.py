import re
from typing import List, Dict, Any, Set
from rapidfuzz import fuzz
from src.matching.match_result import MatchResult

def clean_name(name: str) -> str:
    """
    Cleans name by lowercasing, removing punctuation, and stripping middle initials.
    E.g. "John A. Doe" -> "john doe"
    """
    if not name:
        return ""
    cleaned = name.lower().strip()
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    # Remove single letter words (middle initials)
    cleaned = re.sub(r"\b[a-z]\b", "", cleaned)
    return " ".join(cleaned.split())

def clean_company_name(name: str) -> str:
    """
    Cleans company names to standardise comparison (e.g. Google LLC -> google).
    """
    if not name:
        return ""
    cleaned = name.strip().lower()
    # Remove corporate suffixes
    cleaned = re.sub(r"\b(inc|llc|corp|co|ltd|corporation|incorporated|limited|gmbh|systems|solutions|technologies)\b", "", cleaned)
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    return cleaned.strip()

def check_company_match(co_a: str, co_b: str) -> bool:
    """
    Compares two company names deterministically.
    """
    clean_a = clean_company_name(co_a)
    clean_b = clean_company_name(co_b)
    if not clean_a or not clean_b:
        return False
    if clean_a == clean_b:
        return True
    if len(clean_a) > 3 and len(clean_b) > 3:
        if clean_a in clean_b or clean_b in clean_a:
            return True
    return fuzz.token_sort_ratio(clean_a, clean_b) > 85

def get_companies(record: Dict[str, Any]) -> Set[str]:
    """
    Gathers all company mentions from current_company or experiences.
    """
    companies = set()
    curr = record.get("current_company")
    if curr:
        companies.add(curr)
    exps = record.get("experience") or []
    for exp in exps:
        if isinstance(exp, dict) and exp.get("company"):
            companies.add(exp["company"])
    return companies

def match_any_company(cos_a: Set[str], cos_b: Set[str]) -> bool:
    """
    Checks if any company in A matches any in B.
    """
    for c_a in cos_a:
        for c_b in cos_b:
            if check_company_match(c_a, c_b):
                return True
    return False

def compare_records(record_a: Dict[str, Any], record_b: Dict[str, Any]) -> MatchResult:
    """
    Compares two candidate records and decides if they represent the same candidate.
    1. Email exact match (score 100)
    2. Phone exact match (score 90)
    3. Name similarity > 90 and company match (score = name similarity score)
       If company info is missing on either record, we skip the company match restriction.
    """
    if not record_a or not record_b:
        return MatchResult(False, 0.0, "no_match")
        
    # Rule 1: Email Exact Match
    emails_a = set(record_a.get("emails") or [])
    emails_b = set(record_b.get("emails") or [])
    shared_emails = emails_a.intersection(emails_b)
    if shared_emails:
        return MatchResult(True, 100.0, "email_exact_match")
        
    # Rule 2: Phone Exact Match
    phones_a = set(record_a.get("phones") or [])
    phones_b = set(record_b.get("phones") or [])
    shared_phones = phones_a.intersection(phones_b)
    if shared_phones:
        return MatchResult(True, 90.0, "phone_exact_match")
        
    # Rule 3: Fuzzy Name Match + Company Match
    name_a = record_a.get("full_name") or ""
    name_b = record_b.get("full_name") or ""
    
    if name_a and name_b:
        clean_a = clean_name(name_a)
        clean_b = clean_name(name_b)
        
        name_sim = fuzz.token_sort_ratio(clean_a, clean_b)
        if name_sim > 90.0:
            cos_a = get_companies(record_a)
            cos_b = get_companies(record_b)
            # If company information is available on both, they must match.
            # Otherwise, fallback to name-only matching.
            if cos_a and cos_b:
                if match_any_company(cos_a, cos_b):
                    return MatchResult(True, float(name_sim), "name_company_match")
            else:
                return MatchResult(True, float(name_sim), "name_company_match")
                
    return MatchResult(False, 0.0, "no_match")

def group_records(records: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Groups candidate records into connected component clusters.
    """
    n = len(records)
    if n == 0:
        return []
        
    adj = {i: [] for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            if compare_records(records[i], records[j]).matched:
                adj[i].append(j)
                adj[j].append(i)
                
    visited = [False] * n
    groups = []
    
    for i in range(n):
        if not visited[i]:
            comp = []
            queue = [i]
            visited[i] = True
            while queue:
                curr = queue.pop(0)
                comp.append(records[curr])
                for neighbor in adj[curr]:
                    if not visited[neighbor]:
                        visited[neighbor] = True
                        queue.append(neighbor)
            groups.append(comp)
            
    return groups
