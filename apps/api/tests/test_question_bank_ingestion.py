from sqlalchemy import select

from signalloop_api.models import QuestionBankQuestion, QuestionSource
from signalloop_api.question_bank_ingestion import SOURCE_FILES, import_approved_source_questions
from signalloop_api.question_bank_seed import APPROVED_SOURCES


def _insert_sources(session):
    for source in APPROVED_SOURCES:
        session.add(QuestionSource(**source))
    session.commit()


def test_import_approved_source_questions_classifies_and_deduplicates(session_factory):
    fixture_by_url = {
        config.url: """
* Explain event delegation.
## 1. Explain event delegation.
1) What are synthetic events in React?
* What is the difference between == and ===?
* Newsletter signup should be ignored https://example.com
<summary><b>What are the main Linux process states?</b></summary><br>
**1)** What is a primary key?
"""
        for config in SOURCE_FILES
    }

    def fetcher(url: str) -> str:
        return fixture_by_url[url]

    with session_factory() as session:
        _insert_sources(session)

        first = import_approved_source_questions(session, fetcher=fetcher)
        second = import_approved_source_questions(session, fetcher=fetcher)

        assert first["fetched_sources"] >= 1
        assert first["created_questions"] >= 1
        assert first["errors"] == []
        assert second["created_questions"] == 0

        questions = session.scalars(select(QuestionBankQuestion)).all()
        assert questions
        assert {q.status for q in questions} == {"needs_review"}
        assert all(q.provenance.get("raw_file_url") for q in questions)
        assert any("debugging" in q.cognitive_tags or "systems_thinking" in q.cognitive_tags for q in questions)
        assert all("newsletter" not in q.prompt.lower() for q in questions)
        assert any(
            q.question_type == "technical_concept"
            and "event delegation" in q.title.lower()
            for q in questions
        )
        question_types_by_source = {
            q.source.source_id: q.question_type
            for q in questions
        }
        assert question_types_by_source["sudheerj_react_questions"] == "technical_concept"
        assert question_types_by_source["lydia_js_questions"] == "technical_concept"
        assert question_types_by_source["alexey_data_science_interviews"] == "technical_concept"
        assert question_types_by_source["trimstray_sysadmin_skills"] == "technical_concept"
        assert question_types_by_source["donnemartin_system_design_primer"] == "system_design"
        assert question_types_by_source["yangshun_tech_interview_handbook"] == "tradeoff_judgment"
