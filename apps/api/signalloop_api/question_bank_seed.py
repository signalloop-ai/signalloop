APPROVED_SOURCES = [
    {
        "source_id": "h5bp_frontend_questions",
        "name": "Front-end Developer Interview Questions",
        "url": "https://github.com/h5bp/Front-end-Developer-Interview-Questions",
        "license": "MIT",
        "recommended_use": "direct_import_candidate",
        "attribution_required": False,
        "notes": "Use repo-owned frontend question patterns only; downstream links need separate review.",
    },
    {
        "source_id": "lydia_js_questions",
        "name": "JavaScript Questions",
        "url": "https://github.com/lydiahallie/javascript-questions",
        "license": "MIT",
        "recommended_use": "direct_import_candidate",
        "attribution_required": False,
        "notes": "Useful for JavaScript conceptual prompts after conversion into SignalLoop format.",
    },
    {
        "source_id": "sudheerj_react_questions",
        "name": "ReactJS Interview Questions",
        "url": "https://github.com/sudheerj/reactjs-interview-questions",
        "license": "MIT",
        "recommended_use": "direct_import_candidate",
        "attribution_required": False,
        "notes": "Frontend-heavy React source; review for freshness and avoid trivia-heavy prompts.",
    },
    {
        "source_id": "donnemartin_system_design_primer",
        "name": "System Design Primer",
        "url": "https://github.com/donnemartin/system-design-primer",
        "license": "CC BY 4.0",
        "recommended_use": "direct_import_candidate_with_attribution",
        "attribution_required": True,
        "notes": "Import only repo content, not linked external references. Preserve attribution.",
    },
    {
        "source_id": "alexey_data_science_interviews",
        "name": "Data Science Interviews",
        "url": "https://github.com/alexeygrigorev/data-science-interviews",
        "license": "CC BY 4.0",
        "recommended_use": "direct_import_candidate_with_attribution",
        "attribution_required": True,
        "notes": "Useful for data/ML/SQL prompts after conversion into assessable questions.",
    },
    {
        "source_id": "trimstray_sysadmin_skills",
        "name": "Test Your Sysadmin Skills",
        "url": "https://github.com/trimstray/test-your-sysadmin-skills",
        "license": "MIT",
        "recommended_use": "direct_import_candidate",
        "attribution_required": False,
        "notes": "Useful for platform/SRE fundamentals; convert into role-appropriate scenarios.",
    },
    {
        "source_id": "yangshun_tech_interview_handbook",
        "name": "Tech Interview Handbook",
        "url": "https://github.com/yangshun/tech-interview-handbook",
        "license": "MIT",
        "recommended_use": "direct_import_candidate",
        "attribution_required": False,
        "notes": "Broad SWE source. Filter out linked third-party problem lists and platform-derived items.",
    },
]


SEED_QUESTIONS = [
    {
        "source_source_id": "internal_signal_loop",
        "title": "Standard FastAPI API debugging challenge",
        "question_type": "coding",
        "prompt": (
            "Debug, harden, and extend a FastAPI task-management API. Use public tests and "
            "candidate-written tests to fix validation, ownership, and product-behavior issues, "
            "then explain the implementation trade-offs."
        ),
        "role_tags": ["backend", "python", "fastapi"],
        "skill_tags": ["api_design", "authorization", "validation", "testing"],
        "cognitive_tags": ["debugging", "systems_thinking", "tradeoff_judgment", "critical_ai_usage"],
        "difficulty": "medium",
        "seniority": "mid",
        "estimated_minutes": 35,
        "rubric": {
            "dimensions": [
                "correctness",
                "edge_case_reasoning",
                "test_quality",
                "tradeoff_explanation",
                "ai_collaboration",
            ],
            "scale": "0-4 per dimension",
        },
        "expected_evidence": [
            "public tests pass",
            "candidate adds an edge-case test",
            "final explanation states authorization response reasoning",
        ],
        "package_status": "package_approved",
        "coding_package_kind": "existing_assessment_pack",
        "coding_package_ref": "fastapi_task_api_standard_v2",
        "coding_package_notes": "Uses the existing Standard FastAPI pack. Phase 6 builder can later expose this as one coding question.",
        "generated_by": "internal",
    },
    {
        "source_source_id": "internal_signal_loop",
        "title": "Advanced FastAPI multi-tenant API challenge",
        "question_type": "coding",
        "prompt": (
            "Debug a more complex FastAPI service with authorization, partial-update, archived-data, "
            "and comment-access issues. Implement the required enhancements and explain production "
            "trade-offs around consistency, access control, and observability."
        ),
        "role_tags": ["backend", "python", "fastapi"],
        "skill_tags": ["api_design", "authorization", "multi_tenancy", "testing", "observability"],
        "cognitive_tags": ["debugging", "systems_thinking", "tradeoff_judgment", "chaos_tolerance"],
        "difficulty": "hard",
        "seniority": "senior",
        "estimated_minutes": 60,
        "rubric": {
            "dimensions": [
                "correctness",
                "authorization_reasoning",
                "feature_quality",
                "test_quality",
                "operability",
            ],
            "scale": "0-4 per dimension",
        },
        "expected_evidence": [
            "public tests pass",
            "candidate handles authorization and partial update edge cases",
            "candidate explains production behavior and rollback risks",
        ],
        "package_status": "package_approved",
        "coding_package_kind": "existing_assessment_pack",
        "coding_package_ref": "fastapi_task_api_advanced_v1",
        "coding_package_notes": "Uses the existing Advanced FastAPI pack. Hidden-test usage can be revisited before Phase 6 assessment assembly.",
        "generated_by": "internal",
    },
    {
        "source_source_id": "internal_signal_loop",
        "title": "Node.js API idempotency review",
        "question_type": "coding",
        "prompt": (
            "A TypeScript Node.js API endpoint processes retryable client requests but can create "
            "duplicate side effects under network retries. Identify the failure mode, implement a "
            "small idempotency guard, and describe what should be logged for production debugging."
        ),
        "role_tags": ["backend", "typescript", "nodejs"],
        "skill_tags": ["api_design", "idempotency", "observability", "testing"],
        "cognitive_tags": ["debugging", "systems_thinking", "chaos_tolerance"],
        "difficulty": "medium",
        "seniority": "senior",
        "estimated_minutes": 40,
        "rubric": {
            "dimensions": ["failure_analysis", "implementation", "test_quality", "operability"],
            "scale": "0-4 per dimension",
        },
        "expected_evidence": [
            "candidate identifies retry duplicate risk",
            "implementation prevents repeated side effects",
            "answer includes production logging or monitoring considerations",
        ],
        "package_status": "missing",
        "coding_package_kind": "to_be_generated",
        "coding_package_ref": None,
        "coding_package_notes": "Needs a Node.js/TypeScript starter package, public tests, and runtime validation before assessment use.",
        "generated_by": "ai_draft",
    },
    {
        "source_source_id": "h5bp_frontend_questions",
        "title": "Frontend performance trade-off",
        "question_type": "tradeoff_judgment",
        "prompt": (
            "A React dashboard is slow on first load and also sluggish when filters change. "
            "Explain how you would separate network, rendering, bundle, and state-management causes. "
            "Then choose two fixes you would try first and justify the trade-offs."
        ),
        "role_tags": ["frontend", "react", "typescript"],
        "skill_tags": ["frontend_performance", "react", "debugging"],
        "cognitive_tags": ["debugging", "tradeoff_judgment", "communication_quality"],
        "difficulty": "medium",
        "seniority": "mid",
        "estimated_minutes": 15,
        "rubric": {
            "dimensions": ["diagnostic_structure", "tradeoff_quality", "frontend_specificity"],
            "scale": "0-4 per dimension",
        },
        "expected_evidence": [
            "separates measurement categories",
            "prioritizes fixes based on user impact",
            "mentions validation through profiling or metrics",
        ],
        "generated_by": "source_inspired",
    },
    {
        "source_source_id": "donnemartin_system_design_primer",
        "title": "Multi-tenant API rate limit design",
        "question_type": "system_design",
        "prompt": (
            "Design rate limiting for a multi-tenant API used by both interactive customers and "
            "background integrations. Cover data model, enforcement point, failure behavior, "
            "tenant isolation, and rollout strategy."
        ),
        "role_tags": ["backend", "platform", "system_design"],
        "skill_tags": ["rate_limiting", "multi_tenancy", "api_design", "reliability"],
        "cognitive_tags": ["systems_thinking", "tradeoff_judgment", "communication_quality"],
        "difficulty": "hard",
        "seniority": "senior",
        "estimated_minutes": 20,
        "rubric": {
            "dimensions": ["architecture_fit", "tenant_isolation", "operability", "tradeoffs"],
            "scale": "0-4 per dimension",
        },
        "expected_evidence": [
            "distinguishes customer and integration traffic",
            "states enforcement and storage trade-offs",
            "addresses rollout and observability",
        ],
        "generated_by": "source_inspired",
    },
    {
        "source_source_id": "alexey_data_science_interviews",
        "title": "Analytics pipeline data quality incident",
        "question_type": "tradeoff_judgment",
        "prompt": (
            "A revenue dashboard dropped by 18 percent after a dbt model change, but sales says "
            "bookings are normal. Describe how you would triage the pipeline, validate the metric, "
            "communicate uncertainty, and decide whether to roll back."
        ),
        "role_tags": ["data", "analytics_engineering"],
        "skill_tags": ["sql", "dbt", "data_quality", "incident_debugging"],
        "cognitive_tags": ["logical_reasoning", "debugging", "chaos_tolerance", "communication_quality"],
        "difficulty": "medium",
        "seniority": "mid",
        "estimated_minutes": 18,
        "rubric": {
            "dimensions": ["triage_order", "metric_reasoning", "communication", "rollback_judgment"],
            "scale": "0-4 per dimension",
        },
        "expected_evidence": [
            "checks lineage and recent changes",
            "separates data bug from business movement",
            "communicates confidence and next action",
        ],
        "generated_by": "source_inspired",
    },
    {
        "source_source_id": "trimstray_sysadmin_skills",
        "title": "Production latency spike triage",
        "question_type": "system_design",
        "prompt": (
            "An internal service has intermittent p95 latency spikes after a deployment. "
            "Explain how you would distinguish application, database, network, host, and dependency "
            "causes, and what temporary mitigations you would consider."
        ),
        "role_tags": ["platform", "devops", "sre"],
        "skill_tags": ["observability", "incident_response", "linux", "reliability"],
        "cognitive_tags": ["chaos_tolerance", "debugging", "systems_thinking", "communication_quality"],
        "difficulty": "medium",
        "seniority": "senior",
        "estimated_minutes": 18,
        "rubric": {
            "dimensions": ["hypothesis_quality", "observability_use", "mitigation_judgment", "communication"],
            "scale": "0-4 per dimension",
        },
        "expected_evidence": [
            "forms multiple plausible hypotheses",
            "uses metrics/logs/traces deliberately",
            "states mitigation risks and rollback criteria",
        ],
        "generated_by": "source_inspired",
    },
    {
        "source_source_id": "internal_signal_loop",
        "title": "Critical AI usage boundary",
        "question_type": "communication",
        "prompt": (
            "You used an AI assistant during an ambiguous engineering task. Write a short final "
            "note explaining what you asked AI for, what you independently verified, where you "
            "did not trust the AI answer, and what ownership you take for the final decision."
        ),
        "role_tags": ["backend", "frontend", "data", "platform", "ai"],
        "skill_tags": ["ai_collaboration", "verification", "engineering_ownership"],
        "cognitive_tags": ["critical_ai_usage", "critical_thinking", "communication_quality"],
        "difficulty": "easy",
        "seniority": "mid",
        "estimated_minutes": 8,
        "rubric": {
            "dimensions": ["transparency", "verification", "ownership", "specificity"],
            "scale": "0-4 per dimension",
        },
        "expected_evidence": [
            "candidate distinguishes AI assistance from own reasoning",
            "candidate names verification steps",
            "candidate accepts responsibility for final work",
        ],
        "generated_by": "internal",
    },
]
