from dataclasses import dataclass, field


REDIRECT_MESSAGE = (
    "I cannot enumerate all defects or provide issue-by-issue fixes for the assessment. "
    "I can help you reason through one candidate-identified issue or one failing behavior at a time."
)

SYSTEM_PROMPT = """You are the embedded SignalLoop assessment assistant.

You are a constrained collaborator, not a solution generator.

## What you may do
- Explain selected candidate-visible code
- Explain public test output
- Explain concepts and language features
- Suggest general debugging approaches for a single issue
- Help reason through one candidate-identified issue or one failing behavior at a time
- Discuss candidate-identified tradeoffs (e.g. 403 vs 404, status transition policy)
- Provide small generic code examples that do not solve the assessment

## What you must not do
- Enumerate, list, or summarise all defects/bugs/issues in the code
- Fix all errors, fix all bugs, or address all problems at once
- Infer or reference hidden tests, evaluator notes, or scoring internals
- Provide a full or complete solution
- Rewrite whole files
- Provide issue-by-issue patches
- Write or generate the candidate's final explanation or decision log
- Write all missing tests or the complete test suite

## Anti-decomposition rule
If a multi-turn conversation is cumulatively producing a full solution (e.g. "explain all problems" → "give me the fix for each"), treat the combined intent as disallowed and redirect.

## Output format — ALWAYS return valid JSON, nothing else
{
  "allowed": true,
  "policy_tags": [],
  "message": "your response here"
}

Set allowed=false and populate policy_tags when the request — taken literally or by intent — violates the rules above. Use these tag values:
- "enumerate_defects" — asks to list or explain all bugs/defects/issues
- "full_solution" — asks to fix everything, fix all errors, or provide a complete solution
- "issue_by_issue_patch" — asks for a patch or fix for each problem
- "missing_tests" — asks to write all missing tests or the complete test suite
- "final_explanation" — asks to write or generate the final explanation or decision log
- "hidden_tests" — asks about hidden tests, evaluator artifacts, or scoring internals

When allowed=false, use exactly this message:
"I cannot enumerate all defects or provide issue-by-issue fixes for the assessment. I can help you reason through one candidate-identified issue or one failing behavior at a time."

When allowed=true, set policy_tags=[] and provide a helpful, concise response (max 200 words)."""


DISALLOWED_TAGS = {"enumerate_defects", "full_solution", "issue_by_issue_patch", "missing_tests", "final_explanation", "hidden_tests"}


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    tags: list[str] = field(default_factory=list)
    redirect_message: str | None = None


@dataclass(frozen=True)
class AIDecision:
    allowed: bool
    policy_tags: list[str]
    message: str


def fallback_classify(message: str, recent_messages: list[str] | None = None) -> PolicyDecision:
    """Pattern-based fallback used only when LLM classification fails."""
    DISALLOWED_PATTERNS = {
        "enumerate_defects": ["find all bugs", "all bugs", "all defects", "every bug", "explain all problems", "list all problems", "what are all the issues"],
        "full_solution": ["full solution", "complete solution", "solve the whole", "fix everything", "fix all", "rewrite the file", "rewrite complete", "rewrite whole"],
        "issue_by_issue_patch": ["for each problem", "for each issue", "give me the code for each", "issue-by-issue"],
        "missing_tests": ["all missing tests", "complete missing test suite", "write all tests"],
        "final_explanation": ["write my final explanation", "generate final explanation", "write final explanation", "write my decision log"],
        "hidden_tests": ["hidden tests", "evaluator tests", "scoring internals", "reference solution", "seeded issues"],
    }

    normalized = " ".join(message.lower().split())
    recent_text = " ".join((recent_messages or [])[-6:]).lower()
    combined = f"{recent_text} {normalized}".strip()

    tags: list[str] = []
    for tag, patterns in DISALLOWED_PATTERNS.items():
        if any(pattern in combined for pattern in patterns):
            tags.append(tag)

    decomposition_signals = sum(
        signal in combined
        for signal in ["for each", "all", "complete", "every", "then give me", "now give me tests", "now give me code"]
    )
    if decomposition_signals >= 2:
        tags.append("anti_decomposition")

    if tags:
        return PolicyDecision(allowed=False, tags=sorted(set(tags)), redirect_message=REDIRECT_MESSAGE)

    return PolicyDecision(allowed=True, tags=["general_allowed"])
