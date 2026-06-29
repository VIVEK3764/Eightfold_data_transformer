import logging
from typing import List, Dict, Any
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

def clean_company_name(name: str) -> str:
    """
    Cleans company name for comparison (removes suffixes like inc, llc).
    """
    if not name:
        return ""
    import re
    cleaned = name.lower().strip()
    cleaned = re.sub(r"\b(inc|llc|corp|co|ltd|corporation|incorporated|limited|gmbh|systems|solutions|technologies)\b", "", cleaned)
    return re.sub(r"[^\w\s]", "", cleaned).strip()

def check_company_match(exp_a: List[Dict[str, Any]], exp_b: List[Dict[str, Any]]) -> bool:
    """
    Checks if there is a company match between two experience lists.
    We clean company names and check for non-empty matching substring or high similarity.
    """
    companies_a = {clean_company_name(e.get("company")) for e in exp_a if e.get("company")}
    companies_b = {clean_company_name(e.get("company")) for e in exp_b if e.get("company")}
    
    # Remove empty strings
    companies_a.discard("")
    companies_b.discard("")
    
    if not companies_a or not companies_b:
        return False
        
    for c_a in companies_a:
        for c_b in companies_b:
            if c_a == c_b:
                return True
            # Allow substring match for longer company names
            if len(c_a) > 3 and len(c_b) > 3:
                if c_a in c_b or c_b in c_a:
                    return True
            # Fuzzy match
            if fuzz.ratio(c_a, c_b) > 85:
                return True
                
    return False

def profiles_match(p1: Dict[str, Any], p2: Dict[str, Any]) -> bool:
    """
    Determines if two candidate profiles represent the same person.
    Priority matching rules:
    1. Email Exact Match
    2. Phone Exact Match
    3. Name Similarity > 90% AND Company Match
    """
    # 1. Email Exact Match
    emails1 = set(p1.get("emails") or [])
    emails2 = set(p2.get("emails") or [])
    shared_emails = emails1.intersection(emails2)
    if shared_emails:
        logger.info(f"Identity resolved: Match found by email: {shared_emails}")
        return True
        
    # 2. Phone Exact Match
    phones1 = set(p1.get("phones") or [])
    phones2 = set(p2.get("phones") or [])
    shared_phones = phones1.intersection(phones2)
    if shared_phones:
        logger.info(f"Identity resolved: Match found by phone: {shared_phones}")
        return True
        
    # 3. Name Similarity > 90% AND Company Match
    name1 = p1.get("full_name") or ""
    name2 = p2.get("full_name") or ""
    
    if name1 and name2:
        name_sim = fuzz.token_sort_ratio(name1.lower(), name2.lower())
        if name_sim > 90.0:
            exp1 = p1.get("experience") or []
            exp2 = p2.get("experience") or []
            if check_company_match(exp1, exp2):
                logger.info(f"Identity resolved: Match found by Name similarity ({name_sim:.1f}%) and Company match")
                return True
                
    return False

def resolve_identities(profiles: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Groups a list of candidate profiles into clusters representing unique candidates.
    Uses a standard Connected Components algorithm (DFS-based graph traversal).
    """
    n = len(profiles)
    adj = {i: [] for i in range(n)}
    
    # Build the similarity graph
    for i in range(n):
        for j in range(i + 1, n):
            if profiles_match(profiles[i], profiles[j]):
                adj[i].append(j)
                adj[j].append(i)
                
    # Find connected components
    visited = set()
    clusters = []
    
    for i in range(n):
        if i not in visited:
            cluster = []
            queue = [i]
            visited.add(i)
            while queue:
                node = queue.pop(0)
                cluster.append(profiles[node])
                for neighbor in adj[node]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            clusters.append(cluster)
            
    return clusters
