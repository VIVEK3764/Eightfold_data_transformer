from typing import List, Dict, Any, Tuple
from rapidfuzz import fuzz
from src.models.candidate import Candidate, Skill
from src.config.constants import (
    SOURCE_RELIABILITY,
    CONFIDENCE_AGREEMENT_BONUS,
    CONFIDENCE_CONFLICT_PENALTY,
    NAME_CONFLICT_SIMILARITY_THRESHOLD,
)


def get_reliability(source: str) -> float:
    """Returns the source reliability weight (0–1) for the given source type."""
    return SOURCE_RELIABILITY.get(str(source).lower().strip(), 0.0)


def get_highest_priority_source(sources: List[str]) -> str:
    """Returns the source with the highest reliability from the list."""
    if not sources:
        return "notes"
    return max(sources, key=get_reliability)


def calculate_formula_confidence(
    base_reliability: float, agreement_count: int, conflict_count: int
) -> float:
    """
    Applies the core confidence formula and clamps the result to [0.0, 1.0]:
        confidence = base_reliability
                     + AGREEMENT_BONUS * agreement_count
                     - CONFLICT_PENALTY * conflict_count
    """
    conf = (
        base_reliability
        + CONFIDENCE_AGREEMENT_BONUS * agreement_count
        - CONFIDENCE_CONFLICT_PENALTY * conflict_count
    )
    return float(round(max(0.0, min(1.0, conf)), 3))


def calculate_skill_confidence(
    skill_name: str, records: List[Dict[str, Any]]
) -> Tuple[float, List[str]]:
    """
    Calculates confidence for a skill.
    Skills are additive (multiple sources agreeing raises confidence) and have
    no conflict concept — a skill is present or absent.
    """
    agreeing_sources: List[str] = []
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
    Calculates confidence for the merged full_name.

    Fix (vs original): name variants that are *similar* (> NAME_CONFLICT_SIMILARITY_THRESHOLD)
    are treated as the same name expressed differently (e.g. "John Doe" vs "John Andrew Doe"),
    not as adversarial conflicts. Only genuinely different names penalise confidence.

    This prevents the winning name from being unfairly penalised when the merge engine
    selected it correctly from a higher-priority source.
    """
    if not name:
        return 0.0

    target_name_lower = name.strip().lower()
    agreeing_sources: List[str] = []
    conflicting_sources: List[str] = []

    for rec in records:
        source = rec.get("source", "notes")
        rec_name = rec.get("full_name")
        if not rec_name:
            continue
        rec_name_lower = rec_name.strip().lower()
        if rec_name_lower == target_name_lower:
            agreeing_sources.append(source)
        else:
            # Check if the name is a near-variant (middle name/initial differences).
            similarity = fuzz.token_set_ratio(target_name_lower, rec_name_lower)
            if similarity > NAME_CONFLICT_SIMILARITY_THRESHOLD:
                # Treat as a softer agreement — counts as agreeing, not conflicting.
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
    Calculates confidence for a specific email address.
    Cumulative only — emails are either present or absent, never in conflict.
    """
    agreeing_sources: List[str] = []
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
    Calculates confidence for a specific phone number.
    Cumulative only — phones are either present or absent, never in conflict.
    """
    agreeing_sources: List[str] = []
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


def calculate_candidate_confidence(
    candidate: Candidate, matched_records: List[Dict[str, Any]]
) -> Candidate:
    """
    Enriches the candidate with per-skill confidence scores and calculates
    an overall profile confidence as the weighted average across:
        name | emails | phones | skills

    Empty fields are excluded from the overall average to avoid
    artificially deflating the score for sparse profiles.
    """
    if not matched_records:
        candidate.overall_confidence = 0.0
        return candidate

    # 1. Skill confidences
    skill_confidences: List[float] = []
    for skill in candidate.skills:
        conf, sources = calculate_skill_confidence(skill.name, matched_records)
        skill.confidence = conf
        skill.confidence_reason = sources
        skill_confidences.append(conf)

    # 2. Field-level scores
    field_scores: List[float] = []

    if candidate.full_name:
        field_scores.append(calculate_name_confidence(candidate.full_name, matched_records))

    if candidate.emails:
        email_scores = [calculate_email_confidence(e, matched_records) for e in candidate.emails]
        field_scores.append(sum(email_scores) / len(email_scores))

    if candidate.phones:
        phone_scores = [calculate_phone_confidence(p, matched_records) for p in candidate.phones]
        field_scores.append(sum(phone_scores) / len(phone_scores))

    if skill_confidences:
        field_scores.append(sum(skill_confidences) / len(skill_confidences))

    # 3. Overall average
    candidate.overall_confidence = (
        float(round(sum(field_scores) / len(field_scores), 3)) if field_scores else 0.0
    )

    return candidate
