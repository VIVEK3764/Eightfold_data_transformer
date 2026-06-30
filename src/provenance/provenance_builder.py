from typing import List, Dict, Any
from src.models.candidate import Candidate, Provenance
from src.config.constants import SOURCE_RELIABILITY
from src.merge.merge_engine import sort_records


def get_source_reliability(source_str: str) -> float:
    """
    Infers the reliability weight for a source type string.
    E.g. "resume" or "resume.pdf" → 0.95.
    """
    clean = str(source_str).lower().strip()
    for key, val in SOURCE_RELIABILITY.items():
        if key in clean:
            return val
    return 0.60


def _find_winning_record(
    sorted_records: List[Dict[str, Any]],
    field: str,
    target_value: str,
    *,
    list_field: bool = False,
) -> Dict[str, Any]:
    """
    Locates the highest-priority source record that contains *target_value*
    for *field*.

    For list fields (emails, phones, skills), membership is checked with 'in'.
    For scalar fields (full_name, headline), equality is checked.

    Falls back to the first sorted record if no exact match is found.
    """
    target_lower = target_value.strip().lower()
    for rec in sorted_records:
        val = rec.get(field)
        if list_field:
            items = [str(v).strip().lower() for v in (val or []) if v]
            if target_lower in items:
                return rec
        else:
            if val and str(val).strip().lower() == target_lower:
                return rec
    return sorted_records[0] if sorted_records else {}


def _conflict_method(unique_values: set, default_method: str) -> str:
    """Returns the provenance method string, noting conflicts when they exist."""
    return "winner_selected_from_conflict" if len(unique_values) > 1 else default_method


# ─── Field-level provenance builders ─────────────────────────────────────────

def build_name_provenance(
    candidate: Candidate, sorted_records: List[Dict[str, Any]]
) -> List[Provenance]:
    """Builds provenance for full_name, flagging conflict resolution when applicable."""
    if not candidate.full_name:
        return []

    unique_names = {
        rec.get("full_name", "").strip().lower()
        for rec in sorted_records
        if rec.get("full_name")
    }
    winning = _find_winning_record(sorted_records, "full_name", candidate.full_name)
    source = winning.get("source", "resume")

    return [
        Provenance(
            field="full_name",
            value=candidate.full_name,
            source=source,
            method=_conflict_method(unique_names, "name_extraction"),
            source_confidence=get_source_reliability(source),
        )
    ]


def build_headline_provenance(
    candidate: Candidate, sorted_records: List[Dict[str, Any]]
) -> List[Provenance]:
    """Builds provenance for headline."""
    if not candidate.headline:
        return []

    unique_headlines = {
        rec.get("headline", "").strip().lower()
        for rec in sorted_records
        if rec.get("headline")
    }
    winning = _find_winning_record(sorted_records, "headline", candidate.headline)
    source = winning.get("source", "resume")

    return [
        Provenance(
            field="headline",
            value=candidate.headline,
            source=source,
            method=_conflict_method(unique_headlines, "headline_extraction"),
            source_confidence=get_source_reliability(source),
        )
    ]


def build_email_provenance(
    candidate: Candidate, sorted_records: List[Dict[str, Any]]
) -> List[Provenance]:
    """Builds provenance for every email in the merged profile."""
    provenance_list = []
    for email in candidate.emails:
        winning = _find_winning_record(sorted_records, "emails", email, list_field=True)
        source = winning.get("source", "csv")
        provenance_list.append(
            Provenance(
                field="email",
                value=email,
                source=source,
                method="direct_mapping",
                source_confidence=get_source_reliability(source),
            )
        )
    return provenance_list


def build_phone_provenance(
    candidate: Candidate, sorted_records: List[Dict[str, Any]]
) -> List[Provenance]:
    """Builds provenance for every phone in the merged profile."""
    provenance_list = []
    for phone in candidate.phones:
        winning = _find_winning_record(sorted_records, "phones", phone, list_field=True)
        source = winning.get("source", "csv")
        provenance_list.append(
            Provenance(
                field="phone",
                value=phone,
                source=source,
                method="direct_mapping",
                source_confidence=get_source_reliability(source),
            )
        )
    return provenance_list


def build_skill_provenance(
    candidate: Candidate, sorted_records: List[Dict[str, Any]]
) -> List[Provenance]:
    """Builds provenance for every skill in the merged profile."""
    provenance_list = []
    for skill in candidate.skills:
        winning = _find_winning_record(sorted_records, "skills", skill.name, list_field=True)
        source = winning.get("source", "resume")
        method = "skills_section_extraction" if source == "resume" else "direct_mapping"
        provenance_list.append(
            Provenance(
                field="skill",
                value=skill.name,
                source=source,
                method=method,
                source_confidence=get_source_reliability(source),
            )
        )
    return provenance_list


def build_experience_provenance(
    candidate: Candidate, sorted_records: List[Dict[str, Any]]
) -> List[Provenance]:
    """Builds provenance for every experience entry in the merged profile."""
    provenance_list = []
    for exp in candidate.experience:
        target_co = exp.company.strip().lower()
        found_rec = sorted_records[0] if sorted_records else {}
        for rec in sorted_records:
            exps = rec.get("experience") or []
            if any(
                isinstance(item, dict)
                and (item.get("company") or "").strip().lower() == target_co
                for item in exps
            ):
                found_rec = rec
                break
        source = found_rec.get("source", "resume")
        provenance_list.append(
            Provenance(
                field="experience",
                value=f"{exp.title} at {exp.company}",
                source=source,
                method="experience_extraction",
                source_confidence=get_source_reliability(source),
            )
        )
    return provenance_list


def build_education_provenance(
    candidate: Candidate, sorted_records: List[Dict[str, Any]]
) -> List[Provenance]:
    """Builds provenance for every education entry in the merged profile."""
    provenance_list = []
    for edu in candidate.education:
        target_inst = edu.institution.strip().lower()
        found_rec = sorted_records[0] if sorted_records else {}
        for rec in sorted_records:
            edus = rec.get("education") or []
            if any(
                isinstance(item, dict)
                and (item.get("institution") or "").strip().lower() == target_inst
                for item in edus
            ):
                found_rec = rec
                break
        source = found_rec.get("source", "resume")
        provenance_list.append(
            Provenance(
                field="education",
                value=f"{edu.degree} from {edu.institution}",
                source=source,
                method="education_extraction",
                source_confidence=get_source_reliability(source),
            )
        )
    return provenance_list


# ─── Main orchestrator ────────────────────────────────────────────────────────

def build_candidate_provenance(
    candidate: Candidate, matched_records: List[Dict[str, Any]]
) -> Candidate:
    """
    Enriches candidate.provenance with field-level Provenance objects for every
    significant merged field.

    Fix (vs original): sort_records is computed ONCE here and passed to every
    build_* helper, eliminating 7+ redundant sorts per candidate.
    """
    if not matched_records:
        candidate.provenance = []
        return candidate

    # Pre-sort once (Fix 5)
    sorted_records = sort_records(matched_records)

    provenance: List[Provenance] = []
    provenance.extend(build_name_provenance(candidate, sorted_records))
    provenance.extend(build_headline_provenance(candidate, sorted_records))
    provenance.extend(build_email_provenance(candidate, sorted_records))
    provenance.extend(build_phone_provenance(candidate, sorted_records))
    provenance.extend(build_skill_provenance(candidate, sorted_records))
    provenance.extend(build_experience_provenance(candidate, sorted_records))
    provenance.extend(build_education_provenance(candidate, sorted_records))

    candidate.provenance = provenance
    return candidate
