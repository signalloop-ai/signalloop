# Engineering Evidence Report Structure

## Sections

1. Executive summary
2. Overall recommendation
3. Functional correctness
4. Seeded issue coverage
5. Test quality
6. Security/ownership analysis
7. Design decision quality
8. AI collaboration quality
9. Verification behavior
10. FAVO analysis
11. Timeline
12. Follow-up questions

## Source mapping

| Report section | Data sources |
|---|---|
| Functional correctness | Public and hidden test results |
| Seeded issue coverage | Hidden tests, issue map, final code |
| Test quality | Candidate-written tests |
| Design decisions | Decision log, final code, tests |
| AI collaboration | Chat logs and classification |
| Verification | Test-run timeline and snapshots |
| Ownership | Final explanation and follow-up readiness |

## MVP implementation notes

Phase 9 stores generated reports in `evidence_reports`.

Reports include:

- metadata,
- executive summary,
- overall recommendation,
- scoring fields,
- functional correctness,
- seeded issue coverage,
- test quality,
- security/ownership analysis,
- design decision quality,
- AI collaboration quality,
- verification behavior,
- FAVO analysis,
- timeline,
- follow-up questions.

Scoring fields are deterministic MVP estimates from captured evidence. They do not replace manual evaluator judgment.
