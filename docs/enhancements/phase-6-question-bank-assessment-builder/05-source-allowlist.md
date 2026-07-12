# 05 - Source Allowlist

Status: approved for Phase 6A seed/import work.

## Goal

Define which external sources may seed the Phase 6 question bank.

Source approval is a planning/product decision. Question approval happens later in the Super
Admin product UI.

```text
source approval = allowed to ingest drafts
question approval = allowed to use in assessments
```

## Rules

- Do not ingest from arbitrary URLs.
- Do not ingest from sources with no clear license.
- Do not ingest from paid platforms, books, company interview dumps, or proprietary prep sites.
- Do not import downstream linked content unless that downstream source is separately reviewed.
- Store source URL, license, attribution requirement, and import notes with every imported
  question.
- Imported questions enter `needs_review`, never `approved`.

## Recommended first source decisions

| Source ID | Source | License observed | Recommended use | Rationale / constraints |
|---|---|---:|---|---|
| `h5bp_frontend_questions` | `h5bp/Front-end-Developer-Interview-Questions` | MIT | `direct_import_candidate` | Strong frontend coverage across HTML, CSS, JS, testing, performance, network, and coding. Import only repo-owned question text; external links need separate review. |
| `yangshun_tech_interview_handbook` | `yangshun/tech-interview-handbook` | MIT | `direct_import_candidate` | Strong general SWE, coding, behavioral, system-design preparation content. Filter out linked third-party problem lists and avoid importing platform-derived items. |
| `lydia_js_questions` | `lydiahallie/javascript-questions` | MIT | `direct_import_candidate` | Useful frontend/JavaScript conceptual questions with explanations. Best fit for short-answer or frontend screening drafts; convert into SignalLoop format before review. |
| `donnemartin_system_design_primer` | `donnemartin/system-design-primer` | CC BY 4.0 | `direct_import_candidate_with_attribution` | Useful system-design topics and prompts. Requires attribution. Import only repo content, not linked external articles or architecture references. |
| `alexey_data_science_interviews` | `alexeygrigorev/data-science-interviews` | CC BY 4.0 | `direct_import_candidate_with_attribution` | Useful data science / ML / SQL / Python source for future data and ML roles. Requires attribution and careful conversion from Q&A into assessable prompts. |
| `doppler_awesome_interviews` | `DopplerHQ/awesome-interview-questions` | CC0 for the index | `discovery_only` | Good discovery index, but it mostly links to downstream sources with separate licenses. Do not import linked content without separate approval. |
| `kdn251_interviews` | `kdn251/interviews` | MIT | `inspiration_only_initially` | Repo has MIT license but includes folders/references tied to LeetCode, Cracking the Coding Interview, online judges, and other third-party sources. Use only after source-level filtering proves a path is original and safe. |
| `jwasham_coding_interview_university` | `jwasham/coding-interview-university` | CC BY-SA 4.0 | `inspiration_only` | Useful for taxonomy and study-plan coverage, but share-alike obligations make direct question-bank ingestion undesirable for now. |

## Approval statuses

Use these statuses in the future ingestion configuration:

```text
direct_import_candidate
direct_import_candidate_with_attribution
discovery_only
inspiration_only
excluded
```

Only `direct_import_candidate` and `direct_import_candidate_with_attribution` should be fetched
by the first ingestion pipeline.

## First ingestion recommendation

Start with three sources:

```text
h5bp_frontend_questions
lydia_js_questions
donnemartin_system_design_primer
```

Reason:

- covers frontend, JavaScript, and system design,
- avoids immediate dependency on platform/problem-list sources,
- produces useful non-coding and written-response questions for Phase 6,
- keeps license handling simple enough for the first importer.

Then add:

```text
yangshun_tech_interview_handbook
alexey_data_science_interviews
```

after the importer supports stricter path-level filters and attribution metadata.
