import os
import re
from typing import List, Dict, Any, Optional
from src.normalizers.email import normalize_email
from src.normalizers.phone import normalize_phone
from src.normalizers.skills import normalize_skill

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import docx
except ImportError:
    docx = None

try:
    import pdf2image
    import pytesseract
    from PIL import Image
except ImportError:
    pdf2image = None
    pytesseract = None

# Regex patterns for extraction
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"\+?[0-9][0-9\-.\s()]{8,18}[0-9]")

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extracts text from PDF. Falls back to OCR if direct extraction yields nothing.
    """
    text = ""
    if pdfplumber:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception:
            pass
            
    text = text.strip()
    
    # OCR Fallback path
    if not text and pdf2image and pytesseract:
        try:
            images = pdf2image.convert_from_path(file_path)
            ocr_text = ""
            for img in images:
                ocr_text += pytesseract.image_to_string(img) + "\n"
            text = ocr_text.strip()
        except Exception:
            pass
            
    return text

def extract_text_from_docx(file_path: str) -> str:
    """
    Extracts text from DOCX file.
    """
    text = ""
    if docx:
        try:
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                if para.text:
                    text += para.text + "\n"
        except Exception:
            pass
    return text.strip()

def parse_resume(file_path: str) -> List[Dict[str, Any]]:
    """
    Parses PDF or DOCX resume and maps to intermediate candidate structure.
    """
    if not os.path.exists(file_path):
        return []
        
    source_name = os.path.basename(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    
    text = ""
    if ext == ".pdf":
        text = extract_text_from_pdf(file_path)
    elif ext in [".docx", ".doc"]:
        text = extract_text_from_docx(file_path)
    else:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            pass
            
    if not text:
        return []
        
    # Segment/Parse sections
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    # 1. Name: First meaningful line
    full_name = ""
    for line in lines[:5]:
        # Simple heuristic: Avoid metadata or common headings
        if any(h in line.lower() for h in ["resume", "cv", "curriculum", "page", "contact", "email", "phone", "@"]):
            continue
        # Ensure it contains alphabetical characters and is short
        if re.match(r"^[A-Za-z\s.'\-]+$", line) and len(line.split()) >= 2 and len(line) < 50:
            full_name = line
            break
            
    # 2. Emails: extract and normalize
    emails = []
    raw_emails = EMAIL_REGEX.findall(text)
    for e in raw_emails:
        norm = normalize_email(e)
        if norm and norm not in emails:
            emails.append(norm)
            
    # 3. Phones: extract and normalize
    phones = []
    raw_phones = PHONE_REGEX.findall(text)
    for p in raw_phones:
        # Filter strings that don't have enough digits to prevent false positives
        if len(re.sub(r"\D", "", p)) >= 7:
            norm = normalize_phone(p)
            if norm and norm not in phones:
                phones.append(norm)
                
    # 4. Skills Section Extraction
    skills = []
    skills_section_active = False
    for line in lines:
        if re.match(r"^(skills|technical skills|technologies|core competencies):?$", line.lower()):
            skills_section_active = True
            continue
        if skills_section_active:
            # If we hit another major section header, stop
            if re.match(r"^(experience|education|work history|projects|summary):?$", line.lower()):
                skills_section_active = False
                continue
            # Extract skills (either split by comma or per line)
            if "," in line or ";" in line:
                sep = ";" if ";" in line else ","
                parts = [s.strip() for s in line.split(sep) if s.strip()]
                for p in parts:
                    skills.append(normalize_skill(p))
            else:
                skills.append(normalize_skill(line))
                
    # If no skills section was found or empty, search for keywords heuristically
    if not skills:
        common_words = ["Python", "Java", "JavaScript", "C++", "Docker", "AWS", "Kubernetes", "SQL", "Git"]
        for word in common_words:
            if re.search(rf"\b{re.escape(word)}\b", text.lower()):
                skills.append(normalize_skill(word))
                
    # 5. Experience Section (Simple Extraction)
    experience = []
    exp_section_active = False
    exp_block = []
    for line in lines:
        if re.match(r"^(experience|work experience|work history|employment):?$", line.lower()):
            exp_section_active = True
            continue
        if exp_section_active:
            if re.match(r"^(education|skills|projects|summary):?$", line.lower()):
                exp_section_active = False
                continue
            exp_block.append(line)
            
    # Process experience blocks heuristically
    current_company = ""
    if exp_block:
        # Group lines or just create a raw experience block
        # For simplicity, extract first company name match in experiences
        company_match = re.search(r"\b([A-Z][a-zA-Z0-9\s]+(?:Inc|LLC|Corp|Co|Google|Microsoft|Facebook|Apple|Amazon|Netflix))\b", "\n".join(exp_block))
        if company_match:
            current_company = company_match.group(1).strip()
            
        experience.append({
            "company": current_company or "Unknown Company",
            "title": "Software Engineer",
            "start": None,
            "end": None,
            "summary": "\n".join(exp_block[:10])  # limit to 10 lines
        })
    else:
        # Fallback search for current company in text
        company_match = re.search(r"\b(google|microsoft|amazon|facebook|apple|netflix|uber|stripe)\b", text.lower())
        if company_match:
            current_company = company_match.group(1).capitalize()
            
    # 6. Education Section (Simple Extraction)
    education = []
    edu_section_active = False
    edu_block = []
    for line in lines:
        if re.match(r"^(education|academic background|studies):?$", line.lower()):
            edu_section_active = True
            continue
        if edu_section_active:
            if re.match(r"^(experience|skills|projects|summary):?$", line.lower()):
                edu_section_active = False
                continue
            edu_block.append(line)
            
    if edu_block:
        education.append({
            "institution": edu_block[0],
            "degree": edu_block[1] if len(edu_block) > 1 else None,
            "field": None,
            "end_year": None
        })
        
    # 7. Headline
    headline = ""
    title_regex = re.compile(r"\b(software engineer|developer|manager|architect|data scientist|engineer|designer)\b", re.IGNORECASE)
    for line in lines[:8]:
        if full_name and line.lower() == full_name.lower():
            continue
        if title_regex.search(line) and len(line) < 60:
            headline = re.sub(r"(?i)^(headline|role|position|title|job|candidate)\s*:\s*", "", line).strip()
            break

    # Build raw provenance
    raw_provenance = []
    method = "resume_extraction"
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
        "source": "resume",
        "full_name": full_name,
        "emails": emails,
        "phones": phones,
        "headline": headline,
        "current_company": current_company,
        "skills": skills,
        "experience": experience,
        "education": education,
        "raw_provenance": raw_provenance
    }
    
    return [profile]
