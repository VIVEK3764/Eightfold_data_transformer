import re
import uuid
from typing import List, Dict, Any, Optional
from src.models.candidate import Candidate, Skill, Experience, Education
from src.config.constants import SOURCE_PRIORITY
from src.matching.identity_resolver import clean_company_name

# ─── Priority helpers ────────────────────────────────────────────────────────

def get_priority(source: str) -> int:
    return SOURCE_PRIORITY.get(str(source).lower().strip(), 99)


def sort_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Returns records sorted by source priority (resume first, notes last)."""
    return sorted(records, key=lambda x: get_priority(x.get("source", "")))


# ─── Single-value field merges (priority-wins) ───────────────────────────────

def merge_names(sorted_records: List[Dict[str, Any]]) -> Optional[str]:
    """Selects full_name from the highest-priority source that has one.
    Title-cases the result so all-caps sources ('JOHN DOE') produce clean output.
    """
    for rec in sorted_records:
        name = rec.get("full_name")
        if name:
            cleaned = name.strip()
            # Title-case only if the name is ALL-CAPS (scanner/OCR artifact)
            if cleaned.isupper():
                return cleaned.title()
            return cleaned
    return None


def merge_headline(sorted_records: List[Dict[str, Any]]) -> Optional[str]:
    """Selects headline from the highest-priority source that has one."""
    for rec in sorted_records:
        headline = rec.get("headline")
        if headline:
            return headline.strip()
    return None


def merge_location(sorted_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Selects location from the highest-priority non-empty source."""
    for rec in sorted_records:
        loc = rec.get("location")
        if loc:
            if isinstance(loc, dict) and any(loc.values()):
                return loc
            elif isinstance(loc, str) and loc.strip():
                return {"city": loc.strip()}
    return {}


# ─── Multi-value field merges (union + deduplicate) ──────────────────────────

def merge_emails(records: List[Dict[str, Any]]) -> List[str]:
    """Unions and deduplicates emails across all sources."""
    emails: List[str] = []
    for rec in records:
        for email in rec.get("emails") or []:
            if email and email.strip() not in emails:
                emails.append(email.strip())
    return emails


def merge_phones(records: List[Dict[str, Any]]) -> List[str]:
    """Unions and deduplicates phones across all sources."""
    phones: List[str] = []
    for rec in records:
        for phone in rec.get("phones") or []:
            if phone and phone.strip() not in phones:
                phones.append(phone.strip())
    return phones


def merge_skills(records: List[Dict[str, Any]]) -> List[Skill]:
    """Unions and deduplicates skills (case-insensitive). Returns Skill objects."""
    seen_lower: List[str] = []
    skills: List[Skill] = []
    for rec in records:
        for s in rec.get("skills") or []:
            if not s:
                continue
            name_clean = s.strip()
            if name_clean.lower() not in seen_lower:
                seen_lower.append(name_clean.lower())
                skills.append(Skill(name=name_clean, confidence=0.0, confidence_reason=[]))
    return skills


def merge_links(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merges unique links across all sources (first-seen wins per key)."""
    links: Dict[str, Any] = {}
    for rec in records:
        rec_links = rec.get("links") or {}
        if isinstance(rec_links, dict):
            for k, v in rec_links.items():
                if v and not links.get(k):
                    links[k] = v
    return links


# ─── Structured field merges ─────────────────────────────────────────────────

# Year regex declared at module level (Fix 7: was inside build_candidate body)
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


def _exp_dedup_key(co: str, title: str, start: Optional[str], end: Optional[str]) -> tuple:
    """
    Deduplication key for experience entries.
    Uses cleaned company name (Fix 3) so 'Google' and 'Google LLC' share the same key.
    """
    return (clean_company_name(co), title.lower(), start, end)


def merge_experience(records: List[Dict[str, Any]]) -> List[Experience]:
    """
    Merges unique work experience records across all sources.
    Deduplication uses a normalised company name key to avoid 'Google' vs 'Google LLC'
    creating duplicate entries. Sorts chronologically (newest first).
    """
    seen: set = set()
    raw_entries: List[Experience] = []

    for rec in records:
        for exp in rec.get("experience") or []:
            if not exp or not isinstance(exp, dict):
                continue
            co = (exp.get("company") or "").strip()
            title = (exp.get("title") or "").strip()
            start = (exp.get("start") or "").strip() or None
            end = (exp.get("end") or "").strip() or None
            summary = (exp.get("summary") or "").strip() or None

            if not co or co.lower() in ["unknown company", "unknown", "none", "null"]:
                continue
            # Ignore false-positive company extractions matching candidate name tokens
            cand_name = (rec.get("full_name") or "").lower().split()
            if co.lower() in cand_name:
                continue

            key = _exp_dedup_key(co, title, start, end)
            if key not in seen:
                seen.add(key)
                raw_entries.append(
                    Experience(company=co, title=title or None, start=start, end=end, summary=summary)
                )

    raw_entries.sort(key=lambda e: e.start or "", reverse=True)
    return raw_entries


def _norm_inst_key(inst: str) -> str:
    """Normalizes institution name for deduplication (strips punctuation and date ranges)."""
    clean = re.sub(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\s*[-–]\s*(?:\d{4}|Present|Current)\b|\b\d{4}\s*[-–]\s*(?:\d{4}|Present|Current)\b", "", inst, flags=re.IGNORECASE)
    return re.sub(r"[^\w\s]", "", clean.lower()).split()[0] if clean.split() else ""

def merge_education(records: List[Dict[str, Any]]) -> List[Education]:
    """
    Merges education records across all sources.
    Deduplicates by normalized institution name so 'IIT Patna' across CSV, ATS, and Resume
    combine into a single enriched education profile.
    """
    grouped: Dict[str, Education] = {}
    ordered_keys: List[str] = []

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

            # Strip any trailing date ranges from institution string
            inst_clean = re.sub(r"\s+\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\s*[-–]\s*(?:\d{4}|Present|Current)\b|\s+\b\d{4}\s*[-–]\s*(?:\d{4}|Present|Current)\b", "", inst, flags=re.IGNORECASE).strip()

            norm_key = re.sub(r"[^\w\s]", "", inst_clean.lower())
            # Find if an existing group matches this institution
            matched_key = None
            for existing_key in ordered_keys:
                if norm_key == existing_key or norm_key in existing_key or existing_key in norm_key:
                    matched_key = existing_key
                    break

            if not matched_key:
                ordered_keys.append(norm_key)
                grouped[norm_key] = Education(
                    institution=inst_clean,
                    degree=deg,
                    field=field,
                    end_year=end_year
                )
            else:
                existing = grouped[matched_key]
                # Prefer institution name with proper punctuation/length
                if len(inst_clean) > len(existing.institution) or "," in inst_clean and "," not in existing.institution:
                    existing.institution = inst_clean
                # Take richer degree
                if not existing.degree or (deg and len(deg) > len(existing.degree)):
                    existing.degree = deg
                if not existing.field and field:
                    existing.field = field
                if not existing.end_year and end_year:
                    existing.end_year = end_year

    return [grouped[k] for k in ordered_keys]


# ─── Years-of-experience calculator ──────────────────────────────────────────

def _calculate_years_experience(experience: List[Experience]) -> Optional[int]:
    """
    Heuristically sums years across non-overlapping experience spans.
    Returns None if no date information is available.
    """
    total = 0
    current_year = 2026
    for exp in experience:
        if exp.start and exp.end:
            ys = _YEAR_RE.findall(exp.start)
            ye = _YEAR_RE.findall(exp.end)
            if ys and ye:
                total += max(0, int(ye[0]) - int(ys[0]))
            elif ys and "present" in exp.end.lower():
                total += max(0, current_year - int(ys[0]))
    return total if total > 0 else None


# ─── Main builder ─────────────────────────────────────────────────────────────

def build_candidate(records: List[Dict[str, Any]]) -> Candidate:
    """
    Orchestrates the merge of a group of identity-resolved records into a
    single strongly-typed Candidate object.
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
    years_experience = _calculate_years_experience(experience)

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
        overall_confidence=0.0,
    )
