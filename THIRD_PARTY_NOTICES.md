# Third-Party Notices

SignalLoop's original application code, internal documentation, and
SignalLoop-authored assessment material are licensed under Apache-2.0 unless a
file or directory states otherwise.

This file tracks assessment and question-bank content sources separately from
runtime package dependencies. Runtime dependencies are governed by their own
package metadata and lockfiles.

## Assessment Content Boundary

The included assessment packs are demo/reference material for the open-source
foundation. They are suitable for local development, product demos, and
understanding the evidence model. They should be treated as publicly exposed
content, not as secure production assessment inventory.

Production users should author, review, and calibrate their own assessment
packs and hidden evaluation material before using SignalLoop for real hiring
decisions.

## SignalLoop-Authored Content

- Source: SignalLoop internal authored assessment packs and seed questions.
- Location: `assessment_packs/`, internal question-bank seed records, product
  documentation.
- License: Apache-2.0.
- Notes: Hidden tests, scoring rubrics, and evaluator notes are included for
  transparency in the open-source project. Because they are public, they are
  compromised for real candidate evaluation.

## Approved Question-Bank Source Allowlist

The Phase 6A question-bank governance foundation includes an allowlist of
sources that may seed draft questions. Imported items enter review states and
are not automatically approved for real assessments.

| Source ID | Upstream Project | License Noted In Project | SignalLoop Use |
|---|---|---:|---|
| `h5bp_frontend_questions` | `h5bp/Front-end-Developer-Interview-Questions` | MIT | Direct import candidate; repo-owned content only. |
| `lydia_js_questions` | `lydiahallie/javascript-questions` | MIT | Direct import candidate after conversion to SignalLoop prompt format. |
| `sudheerj_react_questions` | `sudheerj/reactjs-interview-questions` | MIT | Direct import candidate after freshness and originality review. |
| `donnemartin_system_design_primer` | `donnemartin/system-design-primer` | CC BY 4.0 | Direct import candidate with attribution; do not import linked external references. |
| `alexey_data_science_interviews` | `alexeygrigorev/data-science-interviews` | CC BY 4.0 | Direct import candidate with attribution after conversion into assessable prompts. |
| `trimstray_sysadmin_skills` | `trimstray/test-your-sysadmin-skills` | MIT | Direct import candidate for platform/SRE prompts after scenario conversion. |
| `yangshun_tech_interview_handbook` | `yangshun/tech-interview-handbook` | MIT | Direct import candidate with path-level filtering; avoid platform-derived or linked third-party content. |

Additional sources listed as discovery-only or inspiration-only in
`docs/enhancements/phase-6-question-bank-assessment-builder/05-source-allowlist.md`
must not be directly imported without a separate license and provenance review.

## Attribution Requirements

For MIT-licensed source material, retain upstream copyright and license notices
when copying or adapting substantial content.

For CC BY 4.0 source material, preserve attribution metadata in the question
record and public documentation or product UI where the content is displayed.

For any source with unclear, missing, platform-derived, or share-alike licensing,
do not import content into the approved question bank until the licensing path
is explicitly reviewed.
