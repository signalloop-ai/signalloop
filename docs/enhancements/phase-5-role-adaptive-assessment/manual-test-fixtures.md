# Phase 5 Manual Test Fixtures

Use these copy-paste fixtures to manually test the adaptive builder. They are
intentionally broader than the automated test suite so product reviewers can see
supported, partially supported, unsupported, and mixed-role behavior.

## How to use

1. Open the employer portal.
2. Go to Assessments.
3. Select the Adaptive builder creation path.
4. Paste role title, team context, JD, candidate email, and resume.
5. Generate blueprint.
6. Check selected pack, directly tested skills, caveats, and follow-up probes.

Direct coding challenge and Adaptive builder are alternate creation paths. Use
Direct when the employer wants to manually choose Basic or Advanced. Use
Adaptive when the employer wants the system to recommend Basic or Advanced from
the JD/resume blueprint.

The JD and resume fields support paste or upload. Upload accepts `.txt`, `.md`,
`.docx`, and text-based `.pdf` files. DOCX/TXT are the most reliable. PDF works
only when the PDF contains extractable text; scanned PDFs need OCR and should be
pasted manually for now.

Team context is optional. Use it for product/domain context that may not be
obvious from the JD, such as "internal workflow APIs", "fintech payments", or
"AI infrastructure". Leave it blank when the JD already has enough context.

Use this candidate email unless a test needs a different one:

```text
candidate.phase5@example.com
```

## Fixture 1 - Supported Advanced Backend

Purpose: happy path. Should select Advanced FastAPI and show Kubernetes/Postgres
as caveats/follow-ups.

Role title:

```text
Senior Backend Engineer
```

Team context:

```text
Control-plane APIs for a multi-tenant AI infrastructure platform.
```

JD:

```text
We are hiring a Senior Backend Engineer for an AI infrastructure team. The role requires Python, FastAPI, API design, authorization, multi-tenant APIs, reliability, observability, PostgreSQL, Kubernetes basics, and strong AI collaboration.

The team builds internal control-plane APIs for provisioning model-serving workloads. We need engineers who can debug production behavior, protect tenant boundaries, write useful tests, and make safe product tradeoffs under ambiguity.
```

Resume:

```text
Backend engineer with 6 years of experience building Python and FastAPI services. Built internal APIs, Django admin tools, PostgreSQL-backed workflows, Redis caching, background jobs, and AWS deployments.

Uses ChatGPT and Copilot for debugging and test design. No direct Kubernetes ownership, but collaborated with platform teams on deployments and monitoring.
```

Expected:

```text
Assessment: Advanced
Direct coverage: FastAPI, authorization, multi-tenancy, reliability, debugging, tests
Caveats/follow-ups: Kubernetes, PostgreSQL depth, Redis/caching, observability
```

## Fixture 2 - Mostly Unsupported Frontend

Purpose: unsupported-role behavior. Should be explicit that React/TypeScript/UI
skills are not directly assessed by current FastAPI packs.

Role title:

```text
Frontend Platform Engineer
```

Team context:

```text
Design system and performance work for a B2B SaaS dashboard.
```

JD:

```text
We need a Frontend Platform Engineer with deep React, TypeScript, component design, frontend performance, accessibility, form validation, and API integration experience.

The engineer will own design-system components, improve Core Web Vitals, maintain Playwright coverage, and partner with backend engineers on API contracts. AI-assisted engineering experience is preferred.
```

Resume:

```text
Frontend engineer with 5 years of React and TypeScript experience. Built reusable component libraries, complex forms, accessibility improvements, and Playwright tests. Worked with REST API integration and performance profiling.

Uses Copilot regularly for refactoring and test generation.
```

Expected:

```text
Assessment: Future Frontend Platform Assessment blueprint
Caveats/follow-ups: React, TypeScript, component design, accessibility, performance, frontend testing
Important: blueprint is saved but invite sending is disabled until this future module is available
```

## Fixture 3 - Supported Mid Backend Standard

Purpose: should select Standard FastAPI for a mid-level backend API role.

Role title:

```text
Backend Engineer
```

Team context:

```text
Internal task and workflow APIs for operations teams.
```

JD:

```text
We are hiring a Backend Engineer to build and maintain Python APIs. The role requires Python, FastAPI, REST API design, input validation, error handling, authorization, pytest, and clear communication.

The engineer will work on internal workflow tools where correctness and predictable behavior matter more than complex distributed systems.
```

Resume:

```text
Software engineer with 3 years of backend experience. Built Python APIs using FastAPI and Flask. Wrote pytest tests for endpoint behavior, validation, and error handling. Has basic PostgreSQL experience and uses ChatGPT occasionally to understand error messages.
```

Expected:

```text
Assessment: Standard
Direct coverage: Python, FastAPI, API design, validation, authorization, error handling, tests
Caveats/follow-ups: PostgreSQL if detected, but less prominent
```

## Fixture 4 - Backend JD With Weak Resume Overlap

Purpose: tests required gaps. JD is backend-heavy, but resume does not clearly
claim FastAPI/API ownership. The core assessment should still be JD-driven, and
resume gaps should become follow-ups rather than score changes.

Role title:

```text
Backend API Engineer
```

Team context:

```text
Tenant-scoped workflow APIs for customer operations.
```

JD:

```text
We need a Backend API Engineer with Python, FastAPI, REST API design, authorization, input validation, pytest, and reliability experience. The engineer will maintain multi-tenant workflow APIs and must be comfortable debugging permission issues and writing regression tests.
```

Resume:

```text
Software engineer with 4 years of experience in Java, Spring Boot, SQL, and batch data processing. Built internal admin tools and supported production incidents. Has used Python for scripts but has not owned FastAPI services.
```

Expected:

```text
Assessment: Standard or Advanced depending on seniority/skills detected
Skill map: FastAPI/API skills appear as required gaps
Follow-ups: validate transfer from Java/Spring to Python/FastAPI, ask about API authorization and pytest
Important: resume gap should not block invite creation
```

## Fixture 4B - Frontend JD With Default Backend Controls

Purpose: regression case for the UI default state. Even if the role title/family
controls are left as the default backend values, a frontend-dominant JD/resume
should produce a future frontend blueprint, not a backend FastAPI assessment.

Role title:

```text
Senior Backend Engineer
```

Role family:

```text
Backend
```

Team context:

```text
Design system and performance work for a B2B SaaS dashboard.
```

JD:

```text
We need a Frontend Platform Engineer with deep React, TypeScript, component design, frontend performance, accessibility, form validation, and API integration experience.

The engineer will own design-system components, improve Core Web Vitals, maintain Playwright coverage, and partner with backend engineers on API contracts. AI-assisted engineering experience is preferred.
```

Resume:

```text
Frontend engineer with 5 years of React and TypeScript experience. Built reusable component libraries, complex forms, accessibility improvements, and Playwright tests. Worked with REST API integration and performance profiling.

Uses Copilot regularly for refactoring and test generation.
```

Expected:

```text
Assessment: Future Frontend Platform Assessment blueprint
Important: extracted frontend skill dominance should override stale/default backend controls
```

## Fixture 5 - Data Engineering Unsupported

Purpose: tests data/SQL unsupported behavior beyond current automated coverage.

Role title:

```text
Data Engineer
```

Team context:

```text
Customer analytics pipelines and warehouse quality checks.
```

JD:

```text
We are hiring a Data Engineer to build ETL pipelines, SQL transformations, warehouse models, and data quality checks. The role requires strong SQL, data modeling, batch pipeline reliability, warehouse concepts, and incident response for broken dashboards.
```

Resume:

```text
Data engineer with 5 years of experience in SQL, Airflow, dbt, Snowflake, BigQuery, data quality checks, and dashboard reliability. Built ETL pipelines and dimensional models for revenue analytics.
```

Expected:

```text
Assessment: Future Data Engineering Assessment blueprint
Caveats/follow-ups: SQL, ETL pipelines, data modeling, warehouse concepts, data quality
Important: blueprint is saved but invite sending is disabled until this future module is available
```

## Fixture 6 - Infra / Kubernetes Unsupported

Purpose: tests infra-heavy role. Current system should expose Kubernetes/CI/CD/
deployment/incident response as follow-up areas.

Role title:

```text
Platform Engineer
```

Team context:

```text
Kubernetes platform for internal product teams.
```

JD:

```text
We need a Platform Engineer with Kubernetes, Docker, CI/CD, cloud infrastructure, deployment automation, monitoring, incident response, and reliability experience. The engineer will own rollout safety, alert quality, and production debugging across services.
```

Resume:

```text
Platform engineer with 7 years of experience running Kubernetes clusters, Docker-based services, GitHub Actions pipelines, AWS infrastructure, monitoring dashboards, SLOs, and incident response. Has some Python scripting experience but no recent FastAPI work.
```

Expected:

```text
Assessment: Future Platform Engineering Assessment blueprint
Caveats/follow-ups: Kubernetes, Docker, CI/CD, cloud, deployment, monitoring, incident response
Important: blueprint is saved but invite sending is disabled until this future module is available
```

## Fixture 7 - AI / LLM Product Engineer Mixed

Purpose: tests AI skills that are mostly unsupported by current executable packs,
with partial signal from AI collaboration and product judgment.

Role title:

```text
AI Product Engineer
```

Team context:

```text
LLM workflow automation and internal copilots.
```

JD:

```text
We are hiring an AI Product Engineer to build LLM API integrations, prompt workflows, RAG systems, evaluation harnesses, and hallucination guardrails. The role also requires backend API design, Python, reliability, and strong AI safety judgment.
```

Resume:

```text
Engineer with 5 years of Python backend experience and 2 years building LLM products. Integrated OpenAI APIs, built prompt chains, retrieval-augmented generation prototypes, eval scripts, and guardrails for hallucination handling. Uses AI tools daily but verifies output with tests.
```

Expected:

```text
Assessment: Advanced if backend/API signals dominate
Direct/partial coverage: Python/backend/API, AI collaboration, product/security judgment
Caveats/follow-ups: RAG, LLM API integration, eval harnesses, model monitoring
```

## Fixture 8 - Candidate Extra Skills Not Required

Purpose: tests candidate extras. JD is simple backend, resume has extra infra/AI
claims. Extras should not dominate blueprint selection.

Role title:

```text
Backend Engineer
```

Team context:

```text
Internal workflow API maintenance.
```

JD:

```text
We need a Backend Engineer for Python APIs. Required skills are Python, FastAPI, REST API design, input validation, error handling, authorization, pytest, and communication. This is not an infrastructure or AI platform role.
```

Resume:

```text
Backend engineer with Python and FastAPI experience. Also claims Kubernetes, Terraform, LLM API integration, RAG, Redis, PostgreSQL, and model monitoring from side projects.
```

Expected:

```text
Assessment: Standard
Candidate extras: Kubernetes, LLM/RAG, Redis, PostgreSQL/model monitoring appear as extra/follow-up, not core scoring
Important: JD should dominate blueprint selection
```

## Fixture 9 - Non-Technical Role Out Of Scope

Purpose: verifies we do not label every role as a future technical assessment.
Non-technical roles should be rejected as out of scope for SignalLoop's current
assessment roadmap.

Role title:

```text
Enterprise Account Executive
```

Team context:

```text
Enterprise sales for a B2B SaaS product.
```

JD:

```text
We are hiring an Enterprise Account Executive to own pipeline generation, discovery calls, procurement negotiation, stakeholder mapping, forecasting, and quarterly revenue targets.
```

Resume:

```text
Sales professional with experience in enterprise discovery, account planning, negotiation, CRM hygiene, MEDDICC qualification, forecasting, and closing expansion revenue.
```

Expected:

```text
Assessment: out of scope, no blueprint created
Important: UI should explain that this JD does not map to a supported or planned technical assessment family
```

## Fixture 10 - Technical But Not In Roadmap

Purpose: verifies technical roles outside the current roadmap are not presented
as planned assessments unless we explicitly add that family to the roadmap.

Role title:

```text
Mobile Engineer
```

Team context:

```text
Native consumer mobile application.
```

JD:

```text
We need a Mobile Engineer with Swift, Kotlin, iOS, Android, mobile release management, app store deployment, offline sync, and crash analytics experience.
```

Resume:

```text
Mobile engineer with Swift, Kotlin, iOS, Android, App Store releases, Google Play releases, offline-first sync, Crashlytics, and native performance profiling experience.
```

Expected:

```text
Assessment: out of scope, no blueprint created
Important: mobile/native is technical, but it is not in the current supported or planned assessment families
```
