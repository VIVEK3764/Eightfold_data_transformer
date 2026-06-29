from typing import List, Dict, Any, Optional
from src.models.candidate import Candidate, Provenance

SOURCE_RELIABILITY = {
    "resume": 0.95,
    "ats": 0.90,
    "csv": 0.75,
    "notes": 0.60
}

def get_source_reliability(source_str: str) -> float:
    """
    Infers the reliability value from the source name (e.g. "resume.pdf" -> 0.95).
    """
    clean = str(source_str).lower().strip()
    for key, val in SOURCE_RELIABILITY.items():
        if key in clean:
            return val
    return 0.60

def build_name_provenance(candidate: Candidate, records: List[Dict[str, Any]]) -> List[Provenance]:
    """
    Builds provenance for full_name. Tracks if a conflict was resolved.
    """
    if not candidate.full_name:
        return []
        
    target_name = candidate.full_name.strip().lower()
    
    # Collect all unique names across sources
    unique_names = set()
    winning_record = None
    
    # Records sorted by priority (resume first)
    from src.merge.merge_engine import sort_records
    sorted_records = sort_records(records)
    
    for rec in sorted_records:
        name = rec.get("full_name")
        if name:
            name_clean = name.strip().lower()
            unique_names.add(name_clean)
            if name_clean == target_name and not winning_record:
                winning_record = rec
                
    if not winning_record:
        # Fallback to highest priority record
        winning_record = sorted_records[0] if sorted_records else {}
        
    source = winning_record.get("source", "resume")
    
    # Determine method
    if len(unique_names) > 1:
        method = "winner_selected_from_conflict"
    else:
        method = "name_extraction"
        
    return [Provenance(
        field="full_name",
        value=candidate.full_name,
        source=source,
        method=method,
        source_confidence=get_source_reliability(source)
    )]

def build_headline_provenance(candidate: Candidate, records: List[Dict[str, Any]]) -> List[Provenance]:
    """
    Builds provenance for headline. Tracks if conflict occurred.
    """
    if not candidate.headline:
        return []
        
    target_headline = candidate.headline.strip().lower()
    unique_headlines = set()
    winning_record = None
    
    from src.merge.merge_engine import sort_records
    sorted_records = sort_records(records)
    
    for rec in sorted_records:
        headline = rec.get("headline")
        if headline:
            headline_clean = headline.strip().lower()
            unique_headlines.add(headline_clean)
            if headline_clean == target_headline and not winning_record:
                winning_record = rec
                
    if not winning_record:
        winning_record = sorted_records[0] if sorted_records else {}
        
    source = winning_record.get("source", "resume")
    method = "winner_selected_from_conflict" if len(unique_headlines) > 1 else "headline_extraction"
    
    return [Provenance(
        field="headline",
        value=candidate.headline,
        source=source,
        method=method,
        source_confidence=get_source_reliability(source)
    )]

def build_email_provenance(candidate: Candidate, records: List[Dict[str, Any]]) -> List[Provenance]:
    """
    Builds provenance for emails.
    """
    provenance_list = []
    
    for email in candidate.emails:
        target_email = email.strip().lower()
        # Find highest priority record containing this email
        from src.merge.merge_engine import sort_records
        sorted_records = sort_records(records)
        
        found_rec = None
        for rec in sorted_records:
            emails = [e.strip().lower() for e in rec.get("emails") or [] if e]
            if target_email in emails:
                found_rec = rec
                break
                
        source = found_rec.get("source", "csv") if found_rec else "csv"
        provenance_list.append(Provenance(
            field="email",
            value=email,
            source=source,
            method="direct_mapping",
            source_confidence=get_source_reliability(source)
        ))
        
    return provenance_list

def build_phone_provenance(candidate: Candidate, records: List[Dict[str, Any]]) -> List[Provenance]:
    """
    Builds provenance for phones.
    """
    provenance_list = []
    
    for phone in candidate.phones:
        target_phone = phone.strip().lower()
        from src.merge.merge_engine import sort_records
        sorted_records = sort_records(records)
        
        found_rec = None
        for rec in sorted_records:
            phones = [p.strip().lower() for p in rec.get("phones") or [] if p]
            if target_phone in phones:
                found_rec = rec
                break
                
        source = found_rec.get("source", "csv") if found_rec else "csv"
        provenance_list.append(Provenance(
            field="phone",
            value=phone,
            source=source,
            method="direct_mapping",
            source_confidence=get_source_reliability(source)
        ))
        
    return provenance_list

def build_skill_provenance(candidate: Candidate, records: List[Dict[str, Any]]) -> List[Provenance]:
    """
    Builds provenance for skills. Each skill gets represented.
    """
    provenance_list = []
    
    for skill in candidate.skills:
        target_skill = skill.name.strip().lower()
        from src.merge.merge_engine import sort_records
        sorted_records = sort_records(records)
        
        found_rec = None
        for rec in sorted_records:
            skills = [s.strip().lower() for s in rec.get("skills") or [] if s]
            if target_skill in skills:
                found_rec = rec
                break
                
        source = found_rec.get("source", "resume") if found_rec else "resume"
        provenance_list.append(Provenance(
            field="skill",
            value=skill.name,
            source=source,
            method="skills_section_extraction" if source == "resume" else "direct_mapping",
            source_confidence=get_source_reliability(source)
        ))
        
    return provenance_list

def build_experience_provenance(candidate: Candidate, records: List[Dict[str, Any]]) -> List[Provenance]:
    """
    Builds provenance for experience items.
    """
    provenance_list = []
    
    for exp in candidate.experience:
        # Match experience back to source
        target_company = exp.company.strip().lower()
        from src.merge.merge_engine import sort_records
        sorted_records = sort_records(records)
        
        found_rec = None
        for rec in sorted_records:
            exps = rec.get("experience") or []
            for item in exps:
                if isinstance(item, dict) and (item.get("company") or "").strip().lower() == target_company:
                    found_rec = rec
                    break
            if found_rec:
                break
                
        source = found_rec.get("source", "resume") if found_rec else "resume"
        provenance_list.append(Provenance(
            field="experience",
            value=f"{exp.title} at {exp.company}",
            source=source,
            method="experience_extraction",
            source_confidence=get_source_reliability(source)
        ))
        
    return provenance_list

def build_education_provenance(candidate: Candidate, records: List[Dict[str, Any]]) -> List[Provenance]:
    """
    Builds provenance for education items.
    """
    provenance_list = []
    
    for edu in candidate.education:
        target_inst = edu.institution.strip().lower()
        from src.merge.merge_engine import sort_records
        sorted_records = sort_records(records)
        
        found_rec = None
        for rec in sorted_records:
            edus = rec.get("education") or []
            for item in edus:
                if isinstance(item, dict) and (item.get("institution") or "").strip().lower() == target_inst:
                    found_rec = rec
                    break
            if found_rec:
                break
                
        source = found_rec.get("source", "resume") if found_rec else "resume"
        provenance_list.append(Provenance(
            field="education",
            value=f"{edu.degree} from {edu.institution}",
            source=source,
            method="education_extraction",
            source_confidence=get_source_reliability(source)
        ))
        
    return provenance_list

def build_candidate_provenance(candidate: Candidate, matched_records: List[Dict[str, Any]]) -> Candidate:
    """
    Enriches candidate.provenance list with field-level Provenance objects
    assembled from matching source records.
    """
    if not matched_records:
        candidate.provenance = []
        return candidate
        
    provenance = []
    provenance.extend(build_name_provenance(candidate, matched_records))
    provenance.extend(build_headline_provenance(candidate, matched_records))
    provenance.extend(build_email_provenance(candidate, matched_records))
    provenance.extend(build_phone_provenance(candidate, matched_records))
    provenance.extend(build_skill_provenance(candidate, matched_records))
    provenance.extend(build_experience_provenance(candidate, matched_records))
    provenance.extend(build_education_provenance(candidate, matched_records))
    
    candidate.provenance = provenance
    return candidate
