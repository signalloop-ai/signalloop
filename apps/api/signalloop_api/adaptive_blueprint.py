from __future__ import annotations

from signalloop_api.assessment_taxonomy import coverage_for_module, skills_by_id
from signalloop_api.assessment_taxonomy.matching import classify_skill_mapping
from signalloop_api.schemas import DEFAULT_DURATIONS


ADVANCED_SIGNALS = {
    "backend.multi_tenancy",
    "backend.reliability",
    "backend.security_judgment",
    "backend.distributed_systems",
    "backend.observability",
    "eng.security_awareness",
}

SUPPORTED_FASTAPI_FIT_SIGNALS = {
    "backend.fastapi",
    "backend.api_design",
    "backend.validation",
    "backend.authorization",
    "backend.ownership_isolation",
    "backend.state_transitions",
    "backend.error_handling",
    "backend.multi_tenancy",
    "backend.reliability",
    "backend.security_judgment",
}

FUTURE_ASSESSMENT_BY_FAMILY = {
    "frontend": {
        "slug": "future_frontend_platform_v1",
        "level": "future_frontend",
        "label": "Future Frontend Platform Assessment",
        "title_suffix": "Frontend Platform Assessment Blueprint",
    },
    "data": {
        "slug": "future_data_engineering_v1",
        "level": "future_data",
        "label": "Future Data Engineering Assessment",
        "title_suffix": "Data Engineering Assessment Blueprint",
    },
    "infra": {
        "slug": "future_platform_engineering_v1",
        "level": "future_infra",
        "label": "Future Platform Engineering Assessment",
        "title_suffix": "Platform Engineering Assessment Blueprint",
    },
    "ai": {
        "slug": "future_ai_product_engineering_v1",
        "level": "future_ai",
        "label": "Future AI Product Engineering Assessment",
        "title_suffix": "AI Product Engineering Assessment Blueprint",
    },
}


class UnsupportedAssessmentScopeError(ValueError):
    pass


def generate_blueprint_payload(
    *,
    role_title: str,
    role_family: str,
    seniority: str,
    expected_ai_usage: int,
    role_skills: dict,
    candidate_skills: dict | None,
    timing_mode: str,
    evaluator_feedback_mode: str,
    duration_minutes: int | None,
) -> dict:
    skill_mapping = classify_skill_mapping(role_skills, candidate_skills)
    role_skill_ids = set(skill_mapping["role_skill_ids"])
    if _is_explicitly_out_of_scope(role_title):
        raise UnsupportedAssessmentScopeError(
            "This JD maps to a technical role outside the current assessment roadmap."
        )
    if not role_skill_ids:
        raise UnsupportedAssessmentScopeError(
            "This JD does not map to a supported or planned technical assessment family yet."
        )
    future_family = _future_family(role_title, role_family, role_skill_ids)
    if future_family:
        return _future_blueprint_payload(
            role_title=role_title,
            role_family=future_family,
            timing_mode=timing_mode,
            evaluator_feedback_mode=evaluator_feedback_mode,
            duration_minutes=duration_minutes,
            skill_mapping=skill_mapping,
        )
    if not (role_skill_ids & SUPPORTED_FASTAPI_FIT_SIGNALS):
        raise UnsupportedAssessmentScopeError(
            "This JD maps to technical skills outside the current assessment roadmap."
        )
    selected_level = _select_level(role_family, seniority, role_skill_ids)
    module_id = "fastapi_task_api_advanced_v1" if selected_level == "advanced" else "fastapi_task_api_standard_v2"
    coverage = _coverage_payload(module_id)
    title = f"{role_title} Adaptive Backend Assessment"
    duration = duration_minutes or DEFAULT_DURATIONS[selected_level]

    return {
        "title": title,
        "assessment_pack_slug": module_id,
        "assessment_level": selected_level,
        "timing_mode": timing_mode,
        "duration_minutes": duration,
        "evaluator_feedback_mode": evaluator_feedback_mode,
        "skill_mapping": skill_mapping,
        "coverage": coverage,
        "rationale": _rationale(role_title, role_family, seniority, module_id, skill_mapping, expected_ai_usage),
        "follow_up_probes": _follow_up_probes(skill_mapping),
        "caveats": _caveats(skill_mapping, coverage),
    }


def _is_explicitly_out_of_scope(role_title: str) -> bool:
    title = role_title.lower()
    return any(term in title for term in ["mobile", "ios", "android"])


def _future_family(role_title: str, role_family: str, role_skill_ids: set[str]) -> str | None:
    title = role_title.lower()
    if "frontend" in title or "front-end" in title:
        return "frontend"
    if "data engineer" in title:
        return "data"
    if "platform engineer" in title:
        return "infra"

    backend_fit_count = len(role_skill_ids & SUPPORTED_FASTAPI_FIT_SIGNALS)
    family_counts = {
        family: sum(1 for skill_id in role_skill_ids if skill_id.startswith(f"{family}."))
        for family in ("frontend", "data", "infra", "ai")
    }
    for family in ("frontend", "data", "infra"):
        if family_counts[family] >= 2 and family_counts[family] > backend_fit_count:
            return family

    if role_family in {"backend", "fullstack"} and backend_fit_count:
        return None
    if role_family in {"frontend", "data", "infra"}:
        return role_family
    if role_family == "ai" and not (role_skill_ids & SUPPORTED_FASTAPI_FIT_SIGNALS):
        return "ai"
    if any(skill_id.startswith("frontend.") for skill_id in role_skill_ids) and not backend_fit_count:
        return "frontend"
    if any(skill_id.startswith("data.") for skill_id in role_skill_ids) and not backend_fit_count:
        return "data"
    if any(skill_id.startswith("infra.") for skill_id in role_skill_ids) and not backend_fit_count:
        return "infra"
    return None


def _future_blueprint_payload(
    *,
    role_title: str,
    role_family: str,
    timing_mode: str,
    evaluator_feedback_mode: str,
    duration_minutes: int | None,
    skill_mapping: dict,
) -> dict:
    config = FUTURE_ASSESSMENT_BY_FAMILY[role_family]
    skill_defs = skills_by_id()
    role_skill_ids = set(skill_mapping["role_skill_ids"])
    unsupported = sorted(role_skill_ids)
    labels = ", ".join(skill_defs[skill_id].label for skill_id in unsupported[:8])
    duration = duration_minutes or 90
    return {
        "title": f"{role_title} {config['title_suffix']}",
        "assessment_pack_slug": config["slug"],
        "assessment_level": config["level"],
        "timing_mode": timing_mode,
        "duration_minutes": duration,
        "evaluator_feedback_mode": evaluator_feedback_mode,
        "skill_mapping": skill_mapping,
        "coverage": {
            "module_id": config["slug"],
            "assessment_pack_slug": config["slug"],
            "label": f"{config['label']} - planned, not invite-ready",
            "directly_tested": [],
            "partially_tested": [],
            "not_tested": sorted(role_skill_ids),
        },
        "rationale": [
            f"The JD maps primarily to a {config['label'].replace('Future ', '').lower()}.",
            "This is a valid assessment blueprint, but the executable module is on the roadmap rather than available in the current MVP.",
            "Use the listed follow-up probes to understand what the future assessment should cover, or use Direct coding challenge only if you intentionally want limited backend/API evidence.",
        ],
        "follow_up_probes": [
            {
                "source": "future_assessment_scope",
                "skill_id": skill_id,
                "question": f"The future assessment should test {skill_defs[skill_id].label}. Ask the candidate for a concrete work sample, tradeoffs, and verification approach until this module is available.",
            }
            for skill_id in unsupported[:8]
        ],
        "caveats": [
            f"Future assessment planned: {config['label']}.",
            f"Current MVP cannot send this assessment yet. Role skills identified: {labels or 'none mapped'}.",
        ],
    }


def _select_level(role_family: str, seniority: str, role_skill_ids: set[str]) -> str:
    backend_overlap = any(skill_id.startswith("backend.") or skill_id.startswith("eng.") for skill_id in role_skill_ids)
    if not backend_overlap and role_family not in {"backend", "fullstack"}:
        return "standard"
    if seniority in {"senior", "staff"} or role_skill_ids & ADVANCED_SIGNALS:
        return "advanced"
    return "standard"


def _coverage_payload(module_id: str) -> dict:
    coverage = coverage_for_module(module_id)
    return {
        "module_id": coverage.module_id,
        "assessment_pack_slug": coverage.assessment_pack_slug,
        "label": coverage.label,
        "directly_tested": list(coverage.directly_tested),
        "partially_tested": list(coverage.partially_tested),
        "not_tested": list(coverage.not_tested),
    }


def _rationale(
    role_title: str,
    role_family: str,
    seniority: str,
    module_id: str,
    skill_mapping: dict,
    expected_ai_usage: int,
) -> list[str]:
    level_label = "Advanced FastAPI v1" if module_id == "fastapi_task_api_advanced_v1" else "Standard FastAPI v2"
    rationale = [
        f"The role is configured as {seniority} {role_family} for {role_title}.",
        f"{level_label} is the strongest currently supported executable assessment for the matched backend/API skills.",
        "The role/JD determines the comparable core assessment; resume claims drive rationale and follow-up probes.",
    ]
    if skill_mapping["required_overlap"]:
        rationale.append("The candidate resume overlaps with role requirements, so the report will highlight claims validated by the work sample.")
    if skill_mapping["required_gap"]:
        rationale.append("Some role-required skills were not clearly claimed by the resume; these become stretch/follow-up areas, not automatic score penalties.")
    if expected_ai_usage >= 60:
        rationale.append("Expected AI usage is high, so the existing constrained AI-collaboration evidence remains important in interpretation.")
    return rationale


def _follow_up_probes(skill_mapping: dict) -> list[dict]:
    skill_defs = skills_by_id()
    probes: list[dict] = []
    for skill_id in skill_mapping["unsupported_required"][:4]:
        skill = skill_defs[skill_id]
        probes.append({
            "source": "unsupported_required",
            "skill_id": skill_id,
            "question": f"The role needs {skill.label}, which this coding task does not directly test. Ask the candidate to walk through a real design or failure scenario involving it.",
        })
    for skill_id in skill_mapping["unsupported_claimed"][:3]:
        if any(probe["skill_id"] == skill_id for probe in probes):
            continue
        skill = skill_defs[skill_id]
        probes.append({
            "source": "unsupported_claimed",
            "skill_id": skill_id,
            "question": f"The resume claims {skill.label}. Ask for a concrete example, tradeoffs they made, and how they verified the result.",
        })
    for skill_id in skill_mapping["required_overlap"][:3]:
        skill = skill_defs[skill_id]
        probes.append({
            "source": "resume_claim_validation",
            "skill_id": skill_id,
            "question": f"The assessment gives evidence for {skill.label}. Ask the candidate which part of their submission best demonstrates this skill and what they would improve next.",
        })
    return probes[:8]


def _caveats(skill_mapping: dict, coverage: dict) -> list[str]:
    skill_defs = skills_by_id()
    not_tested = set(coverage["not_tested"])
    caveats = []
    unsupported = sorted(set(skill_mapping["unsupported_required"]) | set(skill_mapping["unsupported_claimed"]))
    if unsupported:
        labels = ", ".join(skill_defs[skill_id].label for skill_id in unsupported[:6])
        caveats.append(f"Not directly assessed by the selected coding task: {labels}.")
    role_not_tested = sorted(set(skill_mapping["role_skill_ids"]) & not_tested)
    if role_not_tested:
        labels = ", ".join(skill_defs[skill_id].label for skill_id in role_not_tested[:6])
        caveats.append(f"Role-relevant skills requiring follow-up: {labels}.")
    if not caveats:
        caveats.append("The selected pack covers the strongest currently supported backend/API signals; manual review remains required.")
    return caveats
