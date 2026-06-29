import uuid
from typing import List, Dict, Any, Optional
from src.models.candidate import Candidate, Skill, Experience, Education

SOURCE_PRIORITY = {
    "resume": 1,
    "ats": 2,
    "csv": 3,
    "notes": 4
}

def get_priority(source: str) -> int:
    return SOURCE_PRIORITY.get(str(source).lower().strip(), 99)

def sort_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(records, key=lambda x: get_priority(x.get("source", "")))

def merge_names(sorted_records: List[Dict[str, Any]]) -> Optional[str]:
    """
    Selects name from the highest-priority source.
    """
    for rec in sorted_records:
        name = rec.get("full_name")
        if name:
            return name.strip()
    return None

def merge_headline(sorted_records: List[Dict[str, Any]]) -> Optional[str]:
    """
    Selects headline from the highest-priority source.
    """
    for rec in sorted_records:
        headline = rec.get("headline")
        if headline:
            return headline.strip()
    return None

def merge_emails(records: List[Dict[str, Any]]) -> List[str]:
    """
    Unions and deduplicates emails.
    """
    emails = []
    for rec in records:
        for email in rec.get("emails") or []:
            if email and email.strip() not in emails:
                emails.append(email.strip())
    return emails

def merge_phones(records: List[Dict[str, Any]]) -> List[str]:
    """
    Unions and deduplicates phones.
    """
    phones = []
    for rec in records:
        for phone in rec.get("phones") or []:
            if phone and phone.strip() not in phones:
                phones.append(phone.strip())
    return phones

def merge_skills(records: List[Dict[str, Any]]) -> List[Skill]:
    """
    Unions and deduplicates skills. Returns list of Skill objects.
    """
    seen_names = []
    skills = []
    for rec in records:
        for s in rec.get("skills") or []:
            if not s:
                continue
            name_clean = s.strip()
            if name_clean not in seen_names:
                seen_names.append(name_clean)
                skills.append(Skill(
                    name=name_clean,
                    confidence=0.0,
                    confidence_reason=[]
                ))
    return skills

def merge_experience(records: List[Dict[str, Any]]) -> List[Experience]:
    """
    Merges unique work experience records, removing exact duplicates.
    Sorts chronologically (newest first).
    """
    seen = set()
    raw_entries = []
    
    for rec in records:
        for exp in rec.get("experience") or []:
            if not exp or not isinstance(exp, dict):
                continue
            co = (exp.get("company") or "").strip()
            title = (exp.get("title") or "").strip()
            start = (exp.get("start") or "").strip() or None
            end = (exp.get("end") or "").strip() or None
            summary = (exp.get("summary") or "").strip() or None
            
            if not co:
                continue
                
            key = (co.lower(), title.lower(), start, end)
            if key not in seen:
                seen.add(key)
                raw_entries.append(Experience(
                    company=co,
                    title=title or None,
                    start=start,
                    end=end,
                    summary=summary
                ))
                
    # Sort chronologically (newest first) based on start date string (e.g. YYYY-MM)
    def get_sort_key(exp_obj: Experience) -> str:
        return exp_obj.start or ""
        
    raw_entries.sort(key=get_sort_key, reverse=True)
    return raw_entries

def merge_education(records: List[Dict[str, Any]]) -> List[Education]:
    """
    Merges unique education records, removing duplicates.
    """
    seen = set()
    raw_entries = []
    
    for rec in records:
        for edu in rec.get("education") or []:
            if not edu or not isinstance(edu, dict):
                continue
            inst = (edu.get("institution") or "").strip()
            deg = (edu.get("degree") or "").strip() or None
            field = (edu.get("field") or "").strip() or None
            
            raw_end = edu.get("end_year")
            end_year = None
            if raw_end is not None:
                try:
                    end_year = int(raw_end)
                except ValueError:
                    pass
                    
            if not inst:
                continue
                
            key = (inst.lower(), (deg or "").lower(), (field or "").lower(), end_year)
            if key not in seen:
                seen.add(key)
                raw_entries.append(Education(
                    institution=inst,
                    degree=deg,
                    field=field,
                    end_year=end_year
                ))
                
    return raw_entries

def merge_location(sorted_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Selects location from the highest-priority non-empty source.
    """
    for rec in sorted_records:
        loc = rec.get("location")
        if loc:
            if isinstance(loc, dict) and any(loc.values()):
                return loc
            elif isinstance(loc, str) and loc.strip():
                return {"city": loc.strip()}
    return {}

def merge_links(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merges unique links across all sources.
    """
    links = {}
    for rec in records:
        rec_links = rec.get("links") or {}
        if isinstance(rec_links, dict):
            for k, v in rec_links.items():
                if v and not links.get(k):
                    links[k] = v
    return links

def build_candidate(records: List[Dict[str, Any]]) -> Candidate:
    """
    Orchestrates the merge of a group of matched records into a single Candidate.
    """
    if not records:
        raise ValueError("Cannot merge an empty group of records")
        
    sorted_records = sort_records(records)
    candidate_id = str(uuid.uuid4())
    
    full_name = merge_names(sorted_records)
    emails = merge_emails(records)
    phones = merge_phones(records)
    headline = merge_headline(sorted_records)
    skills = merge_skills(records)
    experience = merge_experience(records)
    education = merge_education(records)
    location = merge_location(sorted_records)
    links = merge_links(records)
    
    # Calculate total years of experience heuristically from sorted experiences if possible
    years_experience = None
    # For now, let's keep it None or aggregate years if dates exist
    total_years = 0
    import re
    year_regex = re.compile(r"\b(19\d{2}|20\d{2})\b")
    for exp in experience:
        if exp.start and exp.end:
            ys = year_regex.findall(exp.start)
            ye = year_regex.findall(exp.end)
            if ys and ye:
                total_years += max(0, int(ye[0]) - int(ys[0]))
            elif ys and "present" in exp.end.lower():
                total_years += max(0, 2026 - int(ys[0]))
    if total_years > 0:
        years_experience = total_years

    return Candidate(
        candidate_id=candidate_id,
        full_name=full_name,
        emails=emails,
        phones=phones,
        location=location,
        links=links,
        headline=headline,
        years_experience=years_experience,
        skills=skills,
        experience=experience,
        education=education,
        provenance=[],
        overall_confidence=0.0
    )
