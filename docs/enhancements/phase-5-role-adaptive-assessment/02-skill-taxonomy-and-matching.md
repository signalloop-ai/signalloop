# 02 - Skill Taxonomy and Matching

Status: planned.

## Goal

Define a standard skill taxonomy that maps job requirements, resume claims, and
assessment-module coverage into one shared language.

The taxonomy is the bridge between:

- JD requirements,
- candidate resume claims,
- supported assessment packs,
- unsupported roadmap areas,
- employer report interpretation.

## Storage direction

Use static versioned files in the repository for v1.

Recommended location:

```text
apps/api/signalloop_api/assessment_taxonomy/
  skills.json
  module_coverage.json
```

Do not build a database-managed taxonomy or admin editing UI in Phase 5.

## Skill object

Each skill should be represented as structured data rather than raw keywords.

Example:

```json
{
  "id": "backend.api_design",
  "label": "API design",
  "family": "backend",
  "aliases": ["REST APIs", "HTTP APIs", "endpoint design", "FastAPI routes"],
  "description": "Designing safe, predictable API behavior and contracts.",
  "assessability": "supported",
  "supported_modules": [
    "fastapi-task-api-standard-v2",
    "fastapi-task-api-advanced-v1"
  ],
  "evidence_types": ["coding", "debugging", "tests", "design_explanation"]
}
```

Assessability values:

- `supported` - directly assessed by at least one current pack.
- `partial` - adjacent signal exists, but not enough to claim direct evidence.
- `unsupported` - taxonomy knows the skill, but no current assessment tests it.

## Initial taxonomy scope

Keep the initial taxonomy broad but modest. Target roughly 50-80 skills.

### Backend

- `backend.python`
- `backend.fastapi`
- `backend.api_design`
- `backend.validation`
- `backend.authorization`
- `backend.ownership_isolation`
- `backend.state_transitions`
- `backend.error_handling`
- `backend.database_modeling`
- `backend.transactions`
- `backend.postgresql`
- `backend.caching`
- `backend.background_jobs`
- `backend.observability`
- `backend.multi_tenancy`
- `backend.reliability`
- `backend.distributed_systems`
- `backend.security_judgment`

### Frontend

- `frontend.react`
- `frontend.typescript`
- `frontend.component_design`
- `frontend.state_management`
- `frontend.forms`
- `frontend.accessibility`
- `frontend.performance`
- `frontend.api_integration`
- `frontend.testing`

### Full-stack

- `fullstack.end_to_end_feature`
- `fullstack.api_ui_integration`
- `fullstack.data_flow`
- `fullstack.product_tradeoffs`

### Infra / DevOps

- `infra.docker`
- `infra.kubernetes`
- `infra.ci_cd`
- `infra.cloud_basics`
- `infra.deployment`
- `infra.incident_response`
- `infra.monitoring`

### Data

- `data.sql`
- `data.etl_pipelines`
- `data.data_modeling`
- `data.warehouse_concepts`
- `data.data_quality`

### ML / AI

- `ai.llm_api_integration`
- `ai.prompt_design`
- `ai.rag`
- `ai.evaluation`
- `ai.inference_serving`
- `ai.model_monitoring`
- `ai.ai_safety`

### Engineering judgment

- `eng.debugging`
- `eng.test_design`
- `eng.tradeoff_reasoning`
- `eng.product_judgment`
- `eng.security_awareness`
- `eng.ai_collaboration`
- `eng.ownership`
- `eng.communication`

## Current module coverage

### Standard FastAPI v2

`fastapi-task-api-standard-v2` covers:

- `backend.python`
- `backend.fastapi`
- `backend.api_design`
- `backend.validation`
- `backend.authorization`
- `backend.ownership_isolation`
- `backend.state_transitions`
- `backend.error_handling`
- `eng.debugging`
- `eng.test_design`
- `eng.tradeoff_reasoning`
- `eng.product_judgment`
- `eng.ai_collaboration`
- `eng.ownership`

### Advanced FastAPI v1

`fastapi-task-api-advanced-v1` covers the Standard set plus stronger signal for:

- `backend.multi_tenancy`
- `backend.reliability`
- `backend.security_judgment`
- `eng.security_awareness`
- `eng.product_judgment`
- `eng.tradeoff_reasoning`

### Partial coverage

Current FastAPI packs may produce partial/adjacent evidence for:

- `backend.distributed_systems` - through reliability and edge-case reasoning,
  not true distributed implementation.
- `backend.observability` - through explanation/follow-up only, not tooling.
- `backend.postgresql` - through API/data-model reasoning only, not a database
  implementation.

## Matching model

The matching pipeline should produce structured extracted skills for both the JD
and resume:

```json
{
  "source": "jd",
  "skills": [
    {
      "skill_id": "backend.fastapi",
      "evidence_text": "FastAPI services",
      "importance": "required",
      "confidence": 0.88
    }
  ]
}
```

Importance values:

- `required`
- `preferred`
- `mentioned`

Confidence values should be advisory only. They must not hide extracted skills
from employer review.

## Skill classifications

After JD and resume extraction, classify skills as:

### Required overlap

Required or preferred by the JD and claimed by the candidate.

Use this for:

- validation rationale,
- directly tested skill focus,
- candidate-specific follow-up probes.

### Required gap

Required or preferred by the JD but not clearly claimed by the candidate.

Use this for:

- stretch probes,
- employer caveats,
- not a direct score penalty unless the core assessment tests it.

### Candidate extra

Claimed by the candidate but not required by the JD.

Use this for:

- optional follow-up context,
- usually lower priority.

### Unsupported required

Required by the JD but no current module directly assesses it.

Use this for:

- explicit report caveats,
- follow-up interview probes,
- future module roadmap signal.

### Unsupported claimed

Claimed by the candidate but no current module directly assesses it.

Use this for:

- report caveats,
- follow-up probes,
- never imply validated evidence.

## LLM role

The LLM may propose extracted skills and aliases from pasted JD/resume text.

The deterministic taxonomy layer must then normalize those proposals to known
skill IDs and assessability states. Unknown skills should be retained as
unmapped text, not silently discarded.

The LLM must not:

- invent new supported skills,
- mark unsupported skills as directly assessed,
- alter scoring rubrics,
- generate hidden tests or evaluator artifacts.

## Acceptance criteria

- A static taxonomy exists and includes current/backend plus roadmap skills.
- Current FastAPI packs have explicit skill coverage mappings.
- Matching can classify JD/resume skills into the five classifications.
- Unsupported skills are preserved and displayed.
- Tests cover overlap, gap, extra, unsupported, and unmapped cases.

