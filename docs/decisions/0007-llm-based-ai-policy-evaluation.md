# ADR: Use LLM-Based AI Policy Evaluation with Fallback Classifier

## Status

Accepted

## Context

SignalLoop's embedded assistant must behave as a constrained collaborator, not a solution generator.

The initial MVP used pattern matching to classify disallowed requests such as asking for all bugs, a full solution, hidden tests, or generated final explanations. During local validation, simple rephrasing could bypass brittle string checks. That is risky because the assistant policy boundary is part of the assessment design, not only a UI convenience.

The product still requires an OpenAI provider abstraction and a local fallback path. The assistant must not receive hidden tests, seeded issue lists, scoring internals, evaluator notes, or reference solutions.

## Decision

Use the LLM call itself to perform both policy classification and response generation.

The system prompt requires JSON output with:

```json
{
  "allowed": true,
  "policy_tags": [],
  "message": "response text"
}
```

When `allowed` is false, the assistant returns the fixed policy redirect message. Known disallowed tags include:

- `enumerate_defects`
- `full_solution`
- `issue_by_issue_patch`
- `missing_tests`
- `final_explanation`
- `hidden_tests`

Keep a pattern-based fallback classifier for local fallback behavior and for cases where the provider response cannot be parsed as valid JSON.

## Consequences

- The policy boundary is more semantic and less dependent on exact phrasing.
- The assistant makes one provider call rather than a separate classification call plus a response call.
- Tests should cover both provider JSON decisions and fallback classification.
- Report generation can use stored `policy_tags` to evaluate AI collaboration behavior.
- The LLM classifier itself must remain constrained by the same candidate-visible context boundary.
- This decision does not permit the assistant to reveal hidden tests, enumerate all defects, generate final explanations, or provide complete solutions.
