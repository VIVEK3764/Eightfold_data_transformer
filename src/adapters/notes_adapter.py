import os
import re
from typing import List, Dict, Any, Optional
from src.normalizers.email import normalize_email
from src.normalizers.phone import normalize_phone
from src.normalizers.skills import normalize_skill

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"\+?[0-9][0-9\-.\s()]{8,18}[0-9]")

def parse_notes(file_path: str) -> List[Dict[str, Any]]:
    """
    Parses a recruiter notes text file.
    Returns a list containing a single candidate profile conformant to the adapter contract.
    """
    if not os.path.exists(file_path):
        return []
        
    try:
        with open(file_path, mode="r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return []
        
    if not text.strip():
        return []
        
    source_name = os.path.basename(file_path)
    
    # 1. Emails
    emails = []
    raw_emails = EMAIL_REGEX.findall(text)
    for e in raw_emails:
        norm = normalize_email(e)
        if norm and norm not in emails:
            emails.append(norm)
            
    # 2. Phones
    phones = []
    raw_phones = PHONE_REGEX.findall(text)
    for p in raw_phones:
        if len(re.sub(r"\D", "", p)) >= 7:
            norm = normalize_phone(p)
            if norm and norm not in phones:
                phones.append(norm)
                
    # 3. Name heuristic: Search for common name pattern
    full_name = ""
    name_match = re.search(r"\b(?:name|candidate|candidate name|spoke with|interviewed)\s*:\s*([A-Za-z\s]+)", text, re.IGNORECASE)
    if name_match:
        full_name = name_match.group(1).split("\n")[0].strip()
    else:
        # Search for capitalised word sequences at start of lines
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for line in lines[:3]:
            words = line.split()
            if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w.isalpha()):
                full_name = line
                break
                
    # 4. Headline heuristic
    headline = ""
    headline_match = re.search(r"\b(?:role|position|title|job|headline)\s*:\s*([A-Za-z\s]+)", text, re.IGNORECASE)
    if headline_match:
        headline = headline_match.group(1).split("\n")[0].strip()
        
    # 5. Current Company heuristic: search for company mentions like "Worked at X for" or "current employer is X"
    current_company = ""
    company_match = re.search(r"\b(?:worked at|employed by|current employer|at|with)\s+([A-Z][a-zA-Z0-9]+)\b", text, re.IGNORECASE)
    if company_match:
        current_company = company_match.group(1).strip()
    else:
        # Check standard list of tech companies as keyword fallback
        tech_companies = ["Google", "Microsoft", "Amazon", "Facebook", "Apple", "Netflix", "Uber", "Stripe"]
        for co in tech_companies:
            if re.search(rf"\b{re.escape(co)}\b", text, re.IGNORECASE):
                current_company = co
                break
                
    # 6. Skills extraction: Search text for known skill names
    skills = []
    # Check for direct list patterns like "skills: python, java"
    skills_match = re.search(r"\b(?:skills|technologies|experience in)\s*:\s*([A-Za-z\s,+#;-]+)", text, re.IGNORECASE)
    if skills_match:
        skills_str = skills_match.group(1).split("\n")[0]
        sep = ";" if ";" in skills_str else ","
        parts = [s.strip() for s in skills_str.split(sep) if s.strip()]
        for p in parts:
            skills.append(normalize_skill(p))
            
    if not skills:
        # Fallback to keyword matching for common tech stack
        keywords = ["Python", "Java", "JavaScript", "C++", "Docker", "AWS", "Kubernetes"]
        for word in keywords:
            if re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE):
                skills.append(normalize_skill(word))
                
    # 7. Experience Block
    experience = []
    if current_company or headline:
        experience.append({
            "company": current_company or "Unknown Company",
            "title": headline or "Software Engineer",
            "start": None,
            "end": None,
            "summary": f"Mentions current company: {current_company}"
        })

    # Collect raw provenance records
    raw_provenance = []
    method = "notes_extraction"
    
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

    profile = {
        "source": "notes",
        "full_name": full_name,
        "emails": emails,
        "phones": phones,
        "headline": headline,
        "current_company": current_company,
        "skills": skills,
        "experience": experience,
        "education": [],
        "raw_provenance": raw_provenance
    }
    
    return [profile]
