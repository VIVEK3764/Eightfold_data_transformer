import csv
import os
from typing import List, Dict, Any
from src.normalizers.email import normalize_email
from src.normalizers.phone import normalize_phone
from src.normalizers.skills import normalize_skill

def parse_csv(file_path: str) -> List[Dict[str, Any]]:
    """
    Parses candidate profiles from a recruiter CSV file.
    Returns a list of candidate dictionaries matching the common adapter contract.
    """
    if not os.path.exists(file_path):
        return []
        
    source_name = os.path.basename(file_path)
    profiles = []
    
    with open(file_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Clean keys to lowercase and strip whitespace
            row = {k.strip().lower() if k else "": v for k, v in row.items()}
            
            # Extract fields
            name_val = row.get("name") or row.get("full_name") or ""
            full_name = name_val.strip()
            
            email_val = row.get("email") or row.get("emails") or ""
            emails = []
            if email_val:
                # Handle comma separated emails
                parts = [e.strip() for e in email_val.split(",") if e.strip()]
                for p in parts:
                    norm = normalize_email(p)
                    if norm:
                        emails.append(norm)
                        
            phone_val = row.get("phone") or row.get("phones") or ""
            phones = []
            if phone_val:
                parts = [p.strip() for p in phone_val.split(",") if p.strip()]
                for p in parts:
                    norm = normalize_phone(p)
                    if norm:
                        phones.append(norm)
                        
            headline = (row.get("headline") or row.get("title") or "").strip()
            current_company = (row.get("current_company") or row.get("company") or "").strip()
            
            skill_val = row.get("skills") or row.get("skill") or ""
            skills = []
            if skill_val:
                # Split on comma or semicolon
                sep = ";" if ";" in skill_val else ","
                parts = [s.strip() for s in skill_val.split(sep) if s.strip()]
                for p in parts:
                    skills.append(normalize_skill(p))
                    
            # Basic experience list matching candidate schema fields
            experience = []
            if current_company or headline:
                experience.append({
                    "company": current_company or "Unknown Company",
                    "title": headline or "Software Engineer",
                    "start": row.get("start") or row.get("start_date") or None,
                    "end": row.get("end") or row.get("end_date") or None,
                    "summary": row.get("summary") or row.get("description") or None
                })
                
            education = []
            edu_inst = row.get("education") or row.get("institution") or row.get("school") or ""
            if edu_inst:
                education.append({
                    "institution": edu_inst.strip(),
                    "degree": row.get("degree") or None,
                    "field": row.get("field") or None,
                    "end_year": None  # Will be mapped in later phases
                })

            # Collect raw provenance records
            raw_provenance = []
            method = "csv_parsing"
            
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
                "source": "csv",
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
