from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any, Literal


Assessability = Literal["supported", "partial", "unsupported"]
EvidenceType = Literal["coding", "debugging", "tests", "design_explanation", "follow_up"]

VALID_ASSESSABILITY = {"supported", "partial", "unsupported"}
VALID_EVIDENCE_TYPES = {"coding", "debugging", "tests", "design_explanation", "follow_up"}


class TaxonomyError(ValueError):
    """Raised when the static skill taxonomy is internally inconsistent."""


@dataclass(frozen=True)
class SkillDefinition:
    id: str
    label: str
    family: str
    aliases: tuple[str, ...]
    description: str
    assessability: Assessability
    supported_modules: tuple[str, ...]
    evidence_types: tuple[EvidenceType, ...]


@dataclass(frozen=True)
class ModuleCoverage:
    module_id: str
    assessment_pack_slug: str
    label: str
    directly_tested: tuple[str, ...]
    partially_tested: tuple[str, ...]
    not_tested: tuple[str, ...]


def _read_json_resource(name: str) -> Any:
    resource = resources.files(__package__).joinpath(name)
    return json.loads(resource.read_text(encoding="utf-8"))


def _string_tuple(value: Any, *, field: str, owner: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise TaxonomyError(f"{owner}.{field} must be a list of non-empty strings")
    return tuple(value)


def _parse_skill(raw: Any) -> SkillDefinition:
    if not isinstance(raw, dict):
        raise TaxonomyError("Each skill must be an object")

    skill_id = raw.get("id")
    if not isinstance(skill_id, str) or not skill_id:
        raise TaxonomyError("Skill id must be a non-empty string")

    assessability = raw.get("assessability")
    if assessability not in VALID_ASSESSABILITY:
        raise TaxonomyError(f"{skill_id}.assessability must be one of {sorted(VALID_ASSESSABILITY)}")

    evidence_types = _string_tuple(raw.get("evidence_types"), field="evidence_types", owner=skill_id)
    invalid_evidence = set(evidence_types) - VALID_EVIDENCE_TYPES
    if invalid_evidence:
        raise TaxonomyError(f"{skill_id}.evidence_types contains invalid values: {sorted(invalid_evidence)}")

    return SkillDefinition(
        id=skill_id,
        label=_required_string(raw, "label", skill_id),
        family=_required_string(raw, "family", skill_id),
        aliases=_string_tuple(raw.get("aliases"), field="aliases", owner=skill_id),
        description=_required_string(raw, "description", skill_id),
        assessability=assessability,
        supported_modules=_string_tuple(raw.get("supported_modules"), field="supported_modules", owner=skill_id),
        evidence_types=evidence_types,
    )


def _parse_coverage(raw: Any) -> ModuleCoverage:
    if not isinstance(raw, dict):
        raise TaxonomyError("Each module coverage entry must be an object")

    module_id = raw.get("module_id")
    if not isinstance(module_id, str) or not module_id:
        raise TaxonomyError("Module coverage module_id must be a non-empty string")

    return ModuleCoverage(
        module_id=module_id,
        assessment_pack_slug=_required_string(raw, "assessment_pack_slug", module_id),
        label=_required_string(raw, "label", module_id),
        directly_tested=_string_tuple(raw.get("directly_tested"), field="directly_tested", owner=module_id),
        partially_tested=_string_tuple(raw.get("partially_tested"), field="partially_tested", owner=module_id),
        not_tested=_string_tuple(raw.get("not_tested"), field="not_tested", owner=module_id),
    )


def _required_string(raw: dict[str, Any], field: str, owner: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value:
        raise TaxonomyError(f"{owner}.{field} must be a non-empty string")
    return value


@lru_cache(maxsize=1)
def load_skills() -> tuple[SkillDefinition, ...]:
    raw = _read_json_resource("skills.json")
    if not isinstance(raw, dict) or not isinstance(raw.get("skills"), list):
        raise TaxonomyError("skills.json must contain a top-level skills array")
    skills = tuple(_parse_skill(item) for item in raw["skills"])
    validate_taxonomy(skills, load_module_coverage())
    return skills


@lru_cache(maxsize=1)
def load_module_coverage() -> tuple[ModuleCoverage, ...]:
    raw = _read_json_resource("module_coverage.json")
    if not isinstance(raw, dict) or not isinstance(raw.get("modules"), list):
        raise TaxonomyError("module_coverage.json must contain a top-level modules array")
    coverage = tuple(_parse_coverage(item) for item in raw["modules"])
    validate_taxonomy(_load_skills_unvalidated(), coverage)
    return coverage


def _load_skills_unvalidated() -> tuple[SkillDefinition, ...]:
    raw = _read_json_resource("skills.json")
    if not isinstance(raw, dict) or not isinstance(raw.get("skills"), list):
        raise TaxonomyError("skills.json must contain a top-level skills array")
    return tuple(_parse_skill(item) for item in raw["skills"])


def skills_by_id(skills: tuple[SkillDefinition, ...] | None = None) -> dict[str, SkillDefinition]:
    return {skill.id: skill for skill in (skills or load_skills())}


def coverage_by_module(coverage: tuple[ModuleCoverage, ...] | None = None) -> dict[str, ModuleCoverage]:
    return {module.module_id: module for module in (coverage or load_module_coverage())}


def coverage_for_module(module_id: str) -> ModuleCoverage:
    coverage = coverage_by_module()
    try:
        return coverage[module_id]
    except KeyError as exc:
        raise TaxonomyError(f"Unknown assessment module: {module_id}") from exc


def validate_taxonomy(
    skills: tuple[SkillDefinition, ...] | None = None,
    coverage: tuple[ModuleCoverage, ...] | None = None,
) -> None:
    skills = skills or _load_skills_unvalidated()
    coverage = coverage or load_module_coverage()

    ids = [skill.id for skill in skills]
    duplicates = sorted({skill_id for skill_id in ids if ids.count(skill_id) > 1})
    if duplicates:
        raise TaxonomyError(f"Duplicate skill ids: {duplicates}")

    skill_ids = set(ids)
    module_ids = [module.module_id for module in coverage]
    duplicate_modules = sorted({module_id for module_id in module_ids if module_ids.count(module_id) > 1})
    if duplicate_modules:
        raise TaxonomyError(f"Duplicate module ids: {duplicate_modules}")

    for module in coverage:
        direct = set(module.directly_tested)
        partial = set(module.partially_tested)
        not_tested = set(module.not_tested)
        referenced = direct | partial | not_tested
        missing = referenced - skill_ids
        if missing:
            raise TaxonomyError(f"{module.module_id} references unknown skill ids: {sorted(missing)}")
        direct_partial_overlap = direct & partial
        if direct_partial_overlap:
            raise TaxonomyError(
                f"{module.module_id} marks skills as both directly and partially tested: {sorted(direct_partial_overlap)}"
            )

    for skill in skills:
        if skill.assessability == "unsupported" and skill.supported_modules:
            raise TaxonomyError(f"{skill.id} is unsupported but lists supported modules")
        for module_id in skill.supported_modules:
            if module_id not in module_ids:
                raise TaxonomyError(f"{skill.id} references unknown supported module: {module_id}")
            module = next(item for item in coverage if item.module_id == module_id)
            if skill.id not in set(module.directly_tested) | set(module.partially_tested):
                raise TaxonomyError(f"{skill.id} lists {module_id}, but module coverage does not include it")
