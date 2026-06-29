from typing import List, Dict, Any, Tuple
from src.models.candidate import Candidate, Skill

SOURCE_RELIABILITY = {
    "resume": 0.95,
    "ats": 0.90,
    "csv": 0.75,
    "notes": 0.60
}

def get_reliability(source: str) -> float:
    return SOURCE_RELIABILITY.get(str(source).lower().strip(), 0.0)

def get_highest_priority_source(sources: List[str]) -> str:
    """
    Returns the source with the highest reliability from the list.
    """
    if not sources:
        return "notes"
    return max(sources, key=get_reliability)

def calculate_formula_confidence(base_reliability: float, agreement_count: int, conflict_count: int) -> float:
    """
    Applies the confidence formula and clamps the result between 0.0 and 1.0.
    """
    conf = base_reliability + 0.05 * agreement_count - 0.10 * conflict_count
    return float(round(max(0.0, min(1.0, conf)), 3))

def calculate_skill_confidence(skill_name: str, records: List[Dict[str, Any]]) -> Tuple[float, List[str]]:
    """
    Calculates confidence for a skill. Skills are cumulative, so conflict count is 0.
    """
    agreeing_sources = []
    for rec in records:
        source = rec.get("source", "notes")
        skills = [s.strip().lower() for s in rec.get("skills") or [] if s]
        if skill_name.strip().lower() in skills:
            agreeing_sources.append(source)
            
    if not agreeing_sources:
        return 0.0, []
        
    base_source = get_highest_priority_source(agreeing_sources)
    base_reliability = get_reliability(base_source)
    
    agreement_count = len(agreeing_sources) - 1
    confidence = calculate_formula_confidence(base_reliability, agreement_count, 0)
    
    return confidence, agreeing_sources

def calculate_name_confidence(name: str, records: List[Dict[str, Any]]) -> float:
    """
    Calculates confidence for the name. Different names are treated as conflicts.
    """
    if not name:
        return 0.0
        
    target_name = name.strip().lower()
    agreeing_sources = []
    conflicting_sources = []
    
    for rec in records:
        source = rec.get("source", "notes")
        rec_name = rec.get("full_name")
        if rec_name:
            rec_name_clean = rec_name.strip().lower()
            if rec_name_clean == target_name:
                agreeing_sources.append(source)
            else:
                conflicting_sources.append(source)
                
    if not agreeing_sources:
        return 0.0
        
    base_source = get_highest_priority_source(agreeing_sources)
    base_reliability = get_reliability(base_source)
    
    agreement_count = len(agreeing_sources) - 1
    conflict_count = len(conflicting_sources)
    
    return calculate_formula_confidence(base_reliability, agreement_count, conflict_count)

def calculate_email_confidence(email: str, records: List[Dict[str, Any]]) -> float:
    """
    Calculates confidence for an email. Cumulative, so conflict is 0.
    """
    agreeing_sources = []
    target_email = email.strip().lower()
    
    for rec in records:
        source = rec.get("source", "notes")
        emails = [e.strip().lower() for e in rec.get("emails") or [] if e]
        if target_email in emails:
            agreeing_sources.append(source)
            
    if not agreeing_sources:
        return 0.0
        
    base_source = get_highest_priority_source(agreeing_sources)
    base_reliability = get_reliability(base_source)
    
    agreement_count = len(agreeing_sources) - 1
    return calculate_formula_confidence(base_reliability, agreement_count, 0)

def calculate_phone_confidence(phone: str, records: List[Dict[str, Any]]) -> float:
    """
    Calculates confidence for a phone number. Cumulative, so conflict is 0.
    """
    agreeing_sources = []
    target_phone = phone.strip().lower()
    
    for rec in records:
        source = rec.get("source", "notes")
        phones = [p.strip().lower() for p in rec.get("phones") or [] if p]
        if target_phone in phones:
            agreeing_sources.append(source)
            
    if not agreeing_sources:
        return 0.0
        
    base_source = get_highest_priority_source(agreeing_sources)
    base_reliability = get_reliability(base_source)
    
    agreement_count = len(agreeing_sources) - 1
    return calculate_formula_confidence(base_reliability, agreement_count, 0)

def calculate_candidate_confidence(candidate: Candidate, matched_records: List[Dict[str, Any]]) -> Candidate:
    """
    Populates confidence scores for the candidate's skills and name, and calculates
    an overall average confidence score across major fields:
      - name
      - emails
      - phones
      - skills
    """
    if not matched_records:
        candidate.overall_confidence = 0.0
        return candidate
        
    # 1. Update skill confidences
    skill_confidences = []
    for skill in candidate.skills:
        conf, sources = calculate_skill_confidence(skill.name, matched_records)
        skill.confidence = conf
        # Pydantic Phase 1 fields: name, confidence, confidence_reason
        skill.confidence_reason = sources
        skill_confidences.append(conf)
        
    # 2. Field confidences for overall calculation
    field_scores = []
    
    # Name confidence
    if candidate.full_name:
        name_conf = calculate_name_confidence(candidate.full_name, matched_records)
        field_scores.append(name_conf)
        
    # Email confidence
    if candidate.emails:
        email_scores = [calculate_email_confidence(e, matched_records) for e in candidate.emails]
        avg_email = sum(email_scores) / len(email_scores) if email_scores else 0.0
        field_scores.append(avg_email)
        
    # Phone confidence
    if candidate.phones:
        phone_scores = [calculate_phone_confidence(p, matched_records) for p in candidate.phones]
        avg_phone = sum(phone_scores) / len(phone_scores) if phone_scores else 0.0
        field_scores.append(avg_phone)
        
    # Skills confidence
    if skill_confidences:
        avg_skills = sum(skill_confidences) / len(skill_confidences)
        field_scores.append(avg_skills)
        
    # 3. Overall average candidate confidence
    if field_scores:
        overall = sum(field_scores) / len(field_scores)
        candidate.overall_confidence = float(round(overall, 3))
    else:
        candidate.overall_confidence = 0.0
        
    return candidate
