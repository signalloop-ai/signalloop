from __future__ import annotations

import re
from dataclasses import dataclass

from signalloop_api.assessment_taxonomy.loader import SkillDefinition, load_skills, skills_by_id


@dataclass(frozen=True)
class ExtractedSkill:
    skill_id: str
    evidence_text: str
    importance: str
    confidence: float


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def _alias_pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias.lower())
    escaped = escaped.replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])")


def extract_skills_from_text(text: str, *, source: str, default_importance: str = "mentioned") -> dict:
    normalized = _normalize_text(text)
    extracted: list[ExtractedSkill] = []
    for skill in load_skills():
        matched_alias = _match_skill(normalized, skill)
        if matched_alias:
            extracted.append(
                ExtractedSkill(
                    skill_id=skill.id,
                    evidence_text=matched_alias,
                    importance=_importance_for_text(normalized, matched_alias, default_importance),
                    confidence=0.82 if matched_alias.lower() == skill.label.lower() else 0.72,
                )
            )

    return {
        "source": source,
        "skills": [
            {
                "skill_id": item.skill_id,
                "evidence_text": item.evidence_text,
                "importance": item.importance,
                "confidence": item.confidence,
            }
            for item in sorted(extracted, key=lambda item: item.skill_id)
        ],
        "unmapped_terms": _extract_unmapped_terms(text, {item.evidence_text.lower() for item in extracted}),
    }


def _match_skill(normalized_text: str, skill: SkillDefinition) -> str | None:
    aliases = [skill.label, *skill.aliases]
    # Prefer longer aliases so "Kubernetes" wins over shorter overlapping terms.
    for alias in sorted(set(aliases), key=len, reverse=True):
        if _alias_pattern(alias).search(normalized_text):
            return alias
    return None


def _importance_for_text(normalized_text: str, alias: str, default_importance: str) -> str:
    idx = normalized_text.find(alias.lower())
    window = normalized_text[max(0, idx - 120): idx + len(alias) + 120] if idx >= 0 else normalized_text
    if any(term in window for term in ["must", "required", "need", "needs", "strong experience", "proficient"]):
        return "required"
    if any(term in window for term in ["preferred", "nice to have", "bonus", "plus"]):
        return "preferred"
    return default_importance


def _extract_unmapped_terms(text: str, mapped_aliases: set[str]) -> list[str]:
    candidates = sorted(set(re.findall(r"\b[A-Z][A-Za-z0-9+#./-]{2,}\b", text)))
    ignored = {"The", "And", "For", "With", "Must", "Needs", "Senior", "Backend", "Engineer"}
    return [
        term for term in candidates
        if term not in ignored and term.lower() not in mapped_aliases
    ][:12]


def classify_skill_mapping(role_skills: dict, candidate_skills: dict | None = None) -> dict:
    skill_defs = skills_by_id()
    role_items = role_skills.get("skills", [])
    candidate_items = (candidate_skills or {}).get("skills", [])

    required_role = {
        item["skill_id"] for item in role_items
        if item.get("importance") in {"required", "preferred"}
    }
    mentioned_role = {item["skill_id"] for item in role_items}
    candidate_claimed = {item["skill_id"] for item in candidate_items}

    role_relevant = required_role or mentioned_role
    required_overlap = sorted(role_relevant & candidate_claimed)
    required_gap = sorted(role_relevant - candidate_claimed)
    candidate_extra = sorted(candidate_claimed - mentioned_role)

    unsupported_required = sorted(
        skill_id for skill_id in role_relevant
        if skill_defs[skill_id].assessability == "unsupported"
    )
    unsupported_claimed = sorted(
        skill_id for skill_id in candidate_claimed
        if skill_defs[skill_id].assessability == "unsupported"
    )

    return {
        "required_overlap": required_overlap,
        "required_gap": required_gap,
        "candidate_extra": candidate_extra,
        "unsupported_required": unsupported_required,
        "unsupported_claimed": unsupported_claimed,
        "role_skill_ids": sorted(mentioned_role),
        "candidate_skill_ids": sorted(candidate_claimed),
        "unmapped_terms": {
            "role": role_skills.get("unmapped_terms", []),
            "candidate": (candidate_skills or {}).get("unmapped_terms", []),
        },
    }
