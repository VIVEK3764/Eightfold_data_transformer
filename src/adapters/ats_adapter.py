import json
import os
from typing import List, Dict, Any, Optional
from src.normalizers.email import normalize_email
from src.normalizers.phone import normalize_phone
from src.normalizers.skills import normalize_skill

# Define clean mapping keys to support candidate JSON schemas flexible variations
FIELD_MAPPINGS = {
    "full_name": ["candidateName", "full_name", "name"],
    "emails": ["contactEmail", "emails", "email"],
    "phones": ["contactPhone", "phones", "phone"],
    "current_company": ["currentEmployer", "current_company", "company"],
    "headline": ["jobTitle", "headline", "title"]
}

def resolve_field(raw: Dict[str, Any], target_key: str) -> Any:
    """
    Look up possible source fields from raw dictionary according to mappings.
    """
    aliases = FIELD_MAPPINGS.get(target_key, [])
    for alias in aliases:
        if alias in raw:
            return raw[alias]
        # Also check lowercased/stripped variations
        for r_key, r_val in raw.items():
            if r_key.strip().lower() == alias.lower():
                return r_val
    return None

def parse_ats(file_path: str) -> List[Dict[str, Any]]:
    """
    Parses candidate profiles from an ATS JSON file.
    Returns a list of dictionaries conforming to the common adapter structure.
    """
    if not os.path.exists(file_path):
        return []
        
    source_name = os.path.basename(file_path)
    
    with open(file_path, mode="r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []
            
    if isinstance(data, dict):
        raw_profiles = [data]
    elif isinstance(data, list):
        raw_profiles = data
    else:
        return []
        
    profiles = []
    
    for raw in raw_profiles:
        raw_name = resolve_field(raw, "full_name") or ""
        full_name = str(raw_name).strip() if raw_name else ""
        
        raw_headline = resolve_field(raw, "headline") or ""
        headline = str(raw_headline).strip() if raw_headline else ""
        
        raw_company = resolve_field(raw, "current_company") or ""
        current_company = str(raw_company).strip() if raw_company else ""
        
        # Email parsing & normalization
        emails = []
        raw_email_field = resolve_field(raw, "emails")
        if raw_email_field:
            if isinstance(raw_email_field, list):
                for e in raw_email_field:
                    norm = normalize_email(str(e))
                    if norm:
                        emails.append(norm)
            else:
                norm = normalize_email(str(raw_email_field))
                if norm:
                    emails.append(norm)
                    
        # Phone parsing & normalization
        phones = []
        raw_phone_field = resolve_field(raw, "phones")
        if raw_phone_field:
            if isinstance(raw_phone_field, list):
                for p in raw_phone_field:
                    norm = normalize_phone(str(p))
                    if norm:
                        phones.append(norm)
            else:
                norm = normalize_phone(str(raw_phone_field))
                if norm:
                    phones.append(norm)
                    
        # Skills parsing & normalization
        skills = []
        raw_skills = raw.get("skills") or raw.get("skill") or []
        if isinstance(raw_skills, list):
            for s in raw_skills:
                skills.append(normalize_skill(str(s)))
        elif isinstance(raw_skills, str):
            parts = [s.strip() for s in raw_skills.split(",") if s.strip()]
            for p in parts:
                skills.append(normalize_skill(p))
                
        # Experience parsing
        experience = []
        raw_exp = raw.get("experience") or raw.get("work_history") or []
        if isinstance(raw_exp, list):
            for item in raw_exp:
                if isinstance(item, dict):
                    experience.append({
                        "company": (item.get("company") or "").strip() or "Unknown Company",
                        "title": (item.get("title") or item.get("job_title") or "").strip() or "Software Engineer",
                        "start": item.get("start") or item.get("start_date") or None,
                        "end": item.get("end") or item.get("end_date") or None,
                        "summary": (item.get("summary") or item.get("description") or "").strip() or None
                    })
                    
        # Education parsing
        education = []
        raw_edu = raw.get("education") or raw.get("studies") or []
        if isinstance(raw_edu, list):
            for item in raw_edu:
                if isinstance(item, dict):
                    edu_year = item.get("end_year") or item.get("year")
                    try:
                        edu_year = int(edu_year) if edu_year is not None else None
                    except ValueError:
                        edu_year = None
                    education.append({
                        "institution": (item.get("institution") or item.get("school") or "").strip() or "Unknown Institution",
                        "degree": (item.get("degree") or "").strip() or None,
                        "field": (item.get("field") or item.get("field_of_study") or "").strip() or None,
                        "end_year": edu_year
                    })

        # Collect raw provenance records
        raw_provenance = []
        method = "ats_parsing"
        
        if full_name:
            raw_provenance.append({"field": "full_name", "value": full_name, "source": source_name, "method": method})
        if headline:
            raw_provenance.append({"field": "headline", "value": headline, "source": source_name, "method": method})
        if current_company:
            raw_provenance.append({"field": "current_company", "value": current_company, "source": source_name, "method": method})
        for email in emails:
            raw_provenance.append({"field": "email", "value": email, "source": source_name, "method": method})
        for phone in phones:
            raw_provenance.append({"field": "phone", "value": phone, "source": source_name, "method": method})
        for skill in skills:
            raw_provenance.append({"field": "skill", "value": skill, "source": source_name, "method": method})

        profiles.append({
            "source": "ats",
            "full_name": full_name,
            "emails": emails,
            "phones": phones,
            "headline": headline,
            "current_company": current_company,
            "skills": skills,
            "experience": experience,
            "education": education,
            "raw_provenance": raw_provenance
        })
        
    return profiles
