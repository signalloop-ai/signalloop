import pytest

from signalloop_api.assessment_taxonomy import (
    ModuleCoverage,
    SkillDefinition,
    TaxonomyError,
    coverage_for_module,
    load_module_coverage,
    load_skills,
    skills_by_id,
    validate_taxonomy,
)


def test_static_taxonomy_loads_and_contains_current_backend_skills() -> None:
    skills = skills_by_id()

    assert len(skills) >= 50
    assert skills["backend.fastapi"].assessability == "supported"
    assert "FastAPI" in skills["backend.fastapi"].aliases
    assert skills["infra.kubernetes"].assessability == "unsupported"
    assert skills["infra.kubernetes"].supported_modules == ()


def test_current_fastapi_modules_have_expected_skill_coverage() -> None:
    standard = coverage_for_module("fastapi_task_api_standard_v2")
    advanced = coverage_for_module("fastapi_task_api_advanced_v1")

    assert standard.assessment_pack_slug == "fastapi_task_api_standard_v2"
    assert "backend.fastapi" in standard.directly_tested
    assert "backend.multi_tenancy" in standard.partially_tested

    assert advanced.assessment_pack_slug == "fastapi_task_api_advanced_v1"
    assert "backend.multi_tenancy" in advanced.directly_tested
    assert "backend.distributed_systems" in advanced.partially_tested
    assert "infra.kubernetes" in advanced.not_tested


def test_taxonomy_validation_accepts_static_files() -> None:
    validate_taxonomy(load_skills(), load_module_coverage())


def test_all_supported_module_claims_are_backed_by_module_coverage() -> None:
    coverage = {module.module_id: module for module in load_module_coverage()}

    for skill in load_skills():
        for module_id in skill.supported_modules:
            module = coverage[module_id]
            assert skill.id in set(module.directly_tested) | set(module.partially_tested)


def test_validation_rejects_unknown_skill_references() -> None:
    skills = (
        SkillDefinition(
            id="backend.python",
            label="Python",
            family="backend",
            aliases=("Python",),
            description="Python skill",
            assessability="supported",
            supported_modules=("example_module",),
            evidence_types=("coding",),
        ),
    )
    coverage = (
        ModuleCoverage(
            module_id="example_module",
            assessment_pack_slug="example_pack",
            label="Example",
            directly_tested=("backend.python", "missing.skill"),
            partially_tested=(),
            not_tested=(),
        ),
    )

    with pytest.raises(TaxonomyError, match="unknown skill ids"):
        validate_taxonomy(skills, coverage)


def test_validation_rejects_supported_module_claim_without_coverage() -> None:
    skills = (
        SkillDefinition(
            id="backend.python",
            label="Python",
            family="backend",
            aliases=("Python",),
            description="Python skill",
            assessability="supported",
            supported_modules=("example_module",),
            evidence_types=("coding",),
        ),
    )
    coverage = (
        ModuleCoverage(
            module_id="example_module",
            assessment_pack_slug="example_pack",
            label="Example",
            directly_tested=(),
            partially_tested=(),
            not_tested=("backend.python",),
        ),
    )

    with pytest.raises(TaxonomyError, match="module coverage does not include"):
        validate_taxonomy(skills, coverage)
