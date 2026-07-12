from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from signalloop_api.models import QuestionBankQuestion, QuestionSource


FetchText = Callable[[str], str]


@dataclass(frozen=True)
class SourceFile:
    source_id: str
    url: str
    role_tags: list[str]
    skill_tags: list[str]
    question_type: str = "technical_concept"
    seniority: str = "mid"
    difficulty: str = "medium"
    estimated_minutes: int = 10
    max_questions: int = 12
    extractor: str = "markdown_questions"


SOURCE_FILES = [
    SourceFile(
        source_id="h5bp_frontend_questions",
        url="https://raw.githubusercontent.com/h5bp/Front-end-Developer-Interview-Questions/main/src/questions/javascript-questions.md",
        role_tags=["frontend", "javascript", "typescript"],
        skill_tags=["javascript", "browser_runtime", "frontend_debugging"],
        max_questions=12,
    ),
    SourceFile(
        source_id="h5bp_frontend_questions",
        url="https://raw.githubusercontent.com/h5bp/Front-end-Developer-Interview-Questions/main/src/questions/performance-questions.md",
        role_tags=["frontend", "performance"],
        skill_tags=["frontend_performance", "web_performance"],
        question_type="tradeoff_judgment",
        max_questions=8,
    ),
    SourceFile(
        source_id="lydia_js_questions",
        url="https://raw.githubusercontent.com/lydiahallie/javascript-questions/master/README.md",
        role_tags=["frontend", "javascript"],
        skill_tags=["javascript", "language_semantics"],
        extractor="numbered_heading_questions",
        max_questions=10,
    ),
    SourceFile(
        source_id="sudheerj_react_questions",
        url="https://raw.githubusercontent.com/sudheerj/reactjs-interview-questions/master/README.md",
        role_tags=["frontend", "react"],
        skill_tags=["react", "component_design"],
        extractor="numbered_markdown_questions",
        max_questions=10,
    ),
    SourceFile(
        source_id="donnemartin_system_design_primer",
        url="https://raw.githubusercontent.com/donnemartin/system-design-primer/master/README.md",
        role_tags=["backend", "platform", "system_design"],
        skill_tags=["system_design", "scalability", "reliability"],
        question_type="system_design",
        seniority="senior",
        estimated_minutes=20,
        extractor="system_design_sections",
        max_questions=8,
    ),
    SourceFile(
        source_id="alexey_data_science_interviews",
        url="https://raw.githubusercontent.com/alexeygrigorev/data-science-interviews/master/technical.md",
        role_tags=["data", "analytics_engineering"],
        skill_tags=["sql", "python", "data_reasoning"],
        question_type="technical_concept",
        estimated_minutes=10,
        extractor="numbered_bold_questions",
        max_questions=12,
    ),
    SourceFile(
        source_id="trimstray_sysadmin_skills",
        url="https://raw.githubusercontent.com/trimstray/test-your-sysadmin-skills/master/README.md",
        role_tags=["platform", "devops", "sre"],
        skill_tags=["linux", "networking", "operations"],
        question_type="technical_concept",
        seniority="mid",
        estimated_minutes=10,
        extractor="html_summary_questions",
        max_questions=14,
    ),
    SourceFile(
        source_id="yangshun_tech_interview_handbook",
        url="https://raw.githubusercontent.com/yangshun/tech-interview-handbook/main/apps/website/blog/2022-04-21-why-you-should-include-debugging-in-the-interview-process.md",
        role_tags=["backend", "frontend", "debugging"],
        skill_tags=["debugging", "testing", "engineering_judgment"],
        question_type="tradeoff_judgment",
        estimated_minutes=12,
        extractor="debugging_prompts",
        max_questions=6,
    ),
]


def fetch_text(url: str) -> str:
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def clean_markdown(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", "", text)
    text = text.replace("`", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_usable_question(text: str) -> bool:
    lowered = text.lower()
    if len(text) < 18 or len(text) > 260:
        return False
    if "http://" in lowered or "https://" in lowered:
        return False
    if any(skip in lowered for skip in ("translation", "sponsor", "newsletter", "contributor", "license")):
        return False
    return "?" in text or lowered.startswith(("explain ", "describe ", "what ", "why ", "how ", "can you "))


def extract_markdown_questions(text: str) -> list[str]:
    questions: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(("* ", "- ")):
            continue
        item = clean_markdown(stripped[2:])
        if is_usable_question(item):
            questions.append(item)
    return questions


def extract_numbered_heading_questions(text: str) -> list[str]:
    questions: list[str] = []
    for match in re.finditer(r"^#+\s*\d+[).]\s*(.+)$", text, flags=re.MULTILINE):
        item = clean_markdown(match.group(1))
        if is_usable_question(item):
            questions.append(item)
    return questions


def extract_numbered_markdown_questions(text: str) -> list[str]:
    questions: list[str] = []
    for match in re.finditer(r"^\s*(?:\d+[).]|[-*])\s*(?:#+\s*)?(?:\*\*)?(.+?)(?:\*\*)?\s*$", text, flags=re.MULTILINE):
        item = clean_markdown(match.group(1))
        if is_usable_question(item):
            questions.append(item)
    return questions


def extract_numbered_bold_questions(text: str) -> list[str]:
    questions: list[str] = []
    for match in re.finditer(r"\*\*\d+\)\*\*\s*(.+?)(?:\n|$)", text):
        item = clean_markdown(match.group(1))
        if is_usable_question(item):
            questions.append(item)
    return questions


def extract_html_summary_questions(text: str) -> list[str]:
    questions: list[str] = []
    for match in re.finditer(r"<summary><b>(.+?)</b></summary>", text, flags=re.DOTALL):
        item = clean_markdown(match.group(1))
        if is_usable_question(item):
            questions.append(item)
    return questions


def extract_system_design_sections(text: str) -> list[str]:
    prompts = [
        "Design a URL shortening service. Explain the API, storage model, scaling bottlenecks, and failure modes.",
        "Design a pastebin-style text sharing service. Cover data model, access patterns, caching, and abuse prevention.",
        "Design a social graph service. Explain read/write paths, fanout strategy, consistency trade-offs, and observability.",
        "Design a web crawler. Cover scheduling, deduplication, politeness, storage, and failure recovery.",
        "Design a cache for expensive queries. Explain invalidation, consistency, capacity, and monitoring trade-offs.",
        "Design a Twitter-like timeline service. Cover fanout, ranking, storage, cache strategy, and degraded behavior.",
    ]
    lowered = text.lower()
    return [prompt for prompt in prompts if any(word in lowered for word in prompt.lower().split()[:3])]


def extract_debugging_prompts(text: str) -> list[str]:
    return [
        "Describe how you would structure a debugging interview so the candidate shows reasoning, not only final code.",
        "Given a flaky production bug, explain how you would narrow the cause, validate a fix, and communicate uncertainty.",
        "Explain what makes a debugging task fair for candidates when AI assistance is allowed but constrained.",
    ]


EXTRACTORS = {
    "markdown_questions": extract_markdown_questions,
    "numbered_heading_questions": extract_numbered_heading_questions,
    "numbered_markdown_questions": extract_numbered_markdown_questions,
    "numbered_bold_questions": extract_numbered_bold_questions,
    "html_summary_questions": extract_html_summary_questions,
    "system_design_sections": extract_system_design_sections,
    "debugging_prompts": extract_debugging_prompts,
}


def classify_cognitive_tags(question: str, question_type: str) -> list[str]:
    lowered = question.lower()
    tags: list[str] = []
    if any(word in lowered for word in ("debug", "bug", "failure", "flaky", "fix", "test")):
        tags.append("debugging")
    if any(word in lowered for word in ("design", "scale", "storage", "cache", "system", "architecture")) or question_type == "system_design":
        tags.append("systems_thinking")
    if any(word in lowered for word in ("trade-off", "tradeoff", "pros", "cons", "why", "choose", "pick")):
        tags.append("tradeoff_judgment")
    if any(word in lowered for word in ("explain", "describe", "communicate")):
        tags.append("communication_quality")
    if any(word in lowered for word in ("incident", "production", "failure", "latency")):
        tags.append("chaos_tolerance")
    if not tags:
        tags = ["logical_reasoning", "communication_quality"]
    return list(dict.fromkeys(tags))


def prompt_from_question(question: str, question_type: str) -> str:
    if question_type in {"system_design", "tradeoff_judgment"} and question.lower().startswith("design "):
        return question
    return (
        f"{question}\n\n"
        "Answer in the context of a realistic engineering role. State assumptions, trade-offs, "
        "verification steps, and how you would communicate risk."
    )


def title_from_question(question: str) -> str:
    title = re.sub(r"[^A-Za-z0-9 ./:_-]", "", question).strip().rstrip("?")
    words = title.split()
    return " ".join(words[:9])[:120] or "Imported question"


def build_question_payload(source: QuestionSource, config: SourceFile, question: str) -> dict:
    cognitive_tags = classify_cognitive_tags(question, config.question_type)
    package_status = "missing" if config.question_type == "coding" else "not_required"
    return {
        "source_id": source.id,
        "status": "needs_review",
        "title": title_from_question(question),
        "question_type": config.question_type,
        "prompt": prompt_from_question(question, config.question_type),
        "role_tags": config.role_tags,
        "skill_tags": config.skill_tags,
        "cognitive_tags": cognitive_tags,
        "difficulty": config.difficulty,
        "seniority": config.seniority,
        "estimated_minutes": config.estimated_minutes,
        "rubric": {
            "dimensions": ["technical_accuracy", "reasoning_quality", "tradeoffs", "communication"],
            "scale": "0-4 per dimension",
        },
        "expected_evidence": [
            "states assumptions",
            "explains reasoning and trade-offs",
            "mentions validation or verification",
        ],
        "provenance": {
            "source_id": source.source_id,
            "source_url": source.url,
            "raw_file_url": config.url,
            "license": source.license,
            "attribution_required": source.attribution_required,
        },
        "generated_by": "source_import",
        "package_status": package_status,
        "coding_package_kind": "source_or_generated_package" if config.question_type == "coding" else None,
        "coding_package_ref": None,
        "coding_package_notes": (
            "Coding package must be imported from source or generated and validated before assessment use."
            if config.question_type == "coding"
            else None
        ),
    }


def import_approved_source_questions(
    session: Session,
    *,
    fetcher: FetchText = fetch_text,
) -> dict:
    source_by_id = {
        source.source_id: source
        for source in session.scalars(select(QuestionSource)).all()
    }
    existing_keys = {
        (question.source_id, question.title)
        for question in session.scalars(select(QuestionBankQuestion)).all()
    }

    created = 0
    fetched_sources = 0
    errors: list[dict] = []
    for config in SOURCE_FILES:
        source = source_by_id.get(config.source_id)
        if source is None or not source.recommended_use.startswith("direct_import_candidate"):
            continue
        try:
            text = fetcher(config.url)
            fetched_sources += 1
            extractor = EXTRACTORS[config.extractor]
            seen: set[str] = set()
            for question_text in extractor(text):
                normalized = clean_markdown(question_text)
                if normalized in seen:
                    continue
                seen.add(normalized)
                payload = build_question_payload(source, config, normalized)
                key = (source.id, payload["title"])
                if key in existing_keys:
                    continue
                session.add(QuestionBankQuestion(**payload))
                existing_keys.add(key)
                created += 1
                if len(seen) >= config.max_questions:
                    break
        except Exception as exc:  # pragma: no cover - exercised via API behavior, exact network errors vary.
            errors.append({"source_id": config.source_id, "url": config.url, "error": str(exc)})
    session.commit()
    return {
        "fetched_sources": fetched_sources,
        "created_questions": created,
        "errors": errors,
    }
