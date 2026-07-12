"use client";

import { useAuth } from "@clerk/nextjs";
import { CheckCircle2, Database, Loader2, RefreshCw, Trash2, XCircle } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  fetchQuestionBankQuestions,
  importSourceQuestions,
  deleteQuestionBankQuestion,
  reviewQuestionBankPackage,
  reviewQuestionBankQuestion,
  seedQuestionBankDrafts,
  updateQuestionBankQuestion,
} from "../api";
import type { QuestionBankQuestion } from "../types";

const STATUS_FILTERS = ["needs_review", "approved", "rejected", "all"] as const;
const DIFFICULTIES = ["easy", "medium", "hard"] as const;
const QUESTION_TYPES = ["coding", "technical_concept", "system_design", "communication", "tradeoff_judgment"] as const;
const QUESTION_TYPE_FILTERS = ["all", ...QUESTION_TYPES] as const;
const PACKAGE_STATUSES = ["missing", "draft", "ready_for_review", "package_approved", "rejected"] as const;

function listValue(value: string[]): string {
  return value.join(", ");
}

function parseList(value: string): string[] {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function statusTone(status: string): string {
  if (status === "approved") return "ready";
  if (status === "rejected") return "error";
  return "warn";
}

function readinessLabel(question: QuestionBankQuestion): string {
  if (question.assessment_ready) return "readiness: assessment ready";
  if (question.question_type === "coding" && question.status === "approved") {
    return "readiness: coding package not approved";
  }
  if (question.question_type === "coding") {
    return "readiness: content/package not ready";
  }
  return "readiness: content not approved";
}

function QuestionReviewCard({
  question,
  onSaved,
  onDeleted,
}: {
  question: QuestionBankQuestion;
  onSaved: (question: QuestionBankQuestion) => void;
  onDeleted: (questionId: number) => void;
}) {
  const { getToken } = useAuth();
  const [title, setTitle] = useState(question.title);
  const [questionType, setQuestionType] = useState(question.question_type);
  const [prompt, setPrompt] = useState(question.prompt);
  const [difficulty, setDifficulty] = useState(question.difficulty);
  const [estimatedMinutes, setEstimatedMinutes] = useState(String(question.estimated_minutes));
  const [roleTags, setRoleTags] = useState(listValue(question.role_tags));
  const [skillTags, setSkillTags] = useState(listValue(question.skill_tags));
  const [cognitiveTags, setCognitiveTags] = useState(listValue(question.cognitive_tags));
  const [packageStatus, setPackageStatus] = useState(question.package_status);
  const [packageKind, setPackageKind] = useState(question.coding_package_kind ?? "");
  const [packageRef, setPackageRef] = useState(question.coding_package_ref ?? "");
  const [packageNotes, setPackageNotes] = useState(question.coding_package_notes ?? "");
  const [reviewNotes, setReviewNotes] = useState(question.review_notes ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const editable = question.status !== "approved";
  const rubricDimensions = Array.isArray(question.rubric.dimensions)
    ? question.rubric.dimensions.join(", ")
    : "No rubric dimensions";

  async function saveMetadata() {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateQuestionBankQuestion(
        question.id,
        {
          title: title.trim(),
          question_type: questionType,
          prompt: prompt.trim(),
          difficulty,
          estimated_minutes: Number(estimatedMinutes),
          role_tags: parseList(roleTags),
          skill_tags: parseList(skillTags),
          cognitive_tags: parseList(cognitiveTags),
          package_status: questionType === "coding" ? packageStatus : "not_required",
          coding_package_kind: questionType === "coding" ? packageKind.trim() || null : null,
          coding_package_ref: questionType === "coding" ? packageRef.trim() || null : null,
          coding_package_notes: questionType === "coding" ? packageNotes.trim() || null : null,
          review_notes: reviewNotes.trim() || null,
        },
        getToken,
      );
      onSaved(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Question update failed");
    } finally {
      setSaving(false);
    }
  }

  async function review(action: "approve" | "reject") {
    setSaving(true);
    setError(null);
    try {
      const updated = await reviewQuestionBankQuestion(question.id, action, reviewNotes.trim(), getToken);
      onSaved(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Question ${action} failed`);
    } finally {
      setSaving(false);
    }
  }

  async function reviewPackage(action: "approve" | "reject") {
    setSaving(true);
    setError(null);
    try {
      const saved = await updateQuestionBankQuestion(
        question.id,
        {
          package_status: packageStatus,
          coding_package_kind: packageKind.trim() || null,
          coding_package_ref: packageRef.trim() || null,
          coding_package_notes: packageNotes.trim() || null,
        },
        getToken,
      );
      const updated = await reviewQuestionBankPackage(saved.id, action, packageNotes.trim(), getToken);
      onSaved(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Coding package ${action} failed`);
    } finally {
      setSaving(false);
    }
  }

  async function deleteQuestion() {
    const confirmed = window.confirm(`Delete "${question.title}" from the question bank?`);
    if (!confirmed) return;
    setSaving(true);
    setError(null);
    try {
      await deleteQuestionBankQuestion(question.id, getToken);
      onDeleted(question.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Question delete failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="employer-section" style={{ display: "grid", gap: 14 }}>
      <div className="section-title">
        <div>
          <h2 style={{ fontSize: 16 }}>{question.title}</h2>
          <p className="attempt-sent-at">
            {question.question_type} · {question.seniority} · {question.estimated_minutes} min
          </p>
        </div>
        <div className="action-row">
          <span className={`status-pill ${statusTone(question.status)}`}>content {question.status.replaceAll("_", " ")}</span>
          <span className={`status-pill ${question.assessment_ready ? "ready" : "warn"}`}>
            {readinessLabel(question)}
          </span>
        </div>
      </div>

      <div className="metric-row">
        <div className="summary-field">
          <span className="summary-field-label">Source</span>
          <span>{question.source?.name ?? "Internal"}</span>
        </div>
        <div className="summary-field">
          <span className="summary-field-label">License</span>
          <span>{question.source?.license ?? "Internal"}</span>
        </div>
        <div className="summary-field">
          <span className="summary-field-label">Generated by</span>
          <span>{question.generated_by}</span>
        </div>
        <div className="summary-field">
          <span className="summary-field-label">Coding package status</span>
          <span>{question.question_type === "coding" ? question.package_status.replaceAll("_", " ") : "not required"}</span>
        </div>
      </div>

      <label className="summary-field">
        <span className="summary-field-label">Title</span>
        <input className="text-input" value={title} disabled={!editable} onChange={(e) => setTitle(e.target.value)} />
      </label>

      <label className="summary-field">
        <span className="summary-field-label">Prompt</span>
        <textarea className="text-input" rows={6} value={prompt} disabled={!editable} onChange={(e) => setPrompt(e.target.value)} />
      </label>

      <div className="metric-row">
        <label className="summary-field">
          <span className="summary-field-label">Question type</span>
          <select className="text-input" value={questionType} disabled={!editable} onChange={(e) => {
            setQuestionType(e.target.value);
            if (e.target.value !== "coding") setPackageStatus("not_required");
            else if (packageStatus === "not_required") setPackageStatus("missing");
          }}>
            {QUESTION_TYPES.map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}
          </select>
        </label>
        <label className="summary-field">
          <span className="summary-field-label">Difficulty</span>
          <select className="text-input" value={difficulty} disabled={!editable} onChange={(e) => setDifficulty(e.target.value)}>
            {DIFFICULTIES.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="summary-field">
          <span className="summary-field-label">Estimated minutes</span>
          <input className="text-input" type="number" min={1} max={240} value={estimatedMinutes} disabled={!editable} onChange={(e) => setEstimatedMinutes(e.target.value)} />
        </label>
      </div>

      <label className="summary-field">
        <span className="summary-field-label">Role tags</span>
        <input className="text-input" value={roleTags} disabled={!editable} onChange={(e) => setRoleTags(e.target.value)} />
      </label>
      <label className="summary-field">
        <span className="summary-field-label">Skill tags</span>
        <input className="text-input" value={skillTags} disabled={!editable} onChange={(e) => setSkillTags(e.target.value)} />
      </label>
      <label className="summary-field">
        <span className="summary-field-label">Cognitive tags</span>
        <input className="text-input" value={cognitiveTags} disabled={!editable} onChange={(e) => setCognitiveTags(e.target.value)} />
      </label>

      {questionType === "coding" ? (
        <div className="employer-section" style={{ display: "grid", gap: 12, padding: 14 }}>
          <div className="section-title">
            <h2 style={{ fontSize: 15 }}>Coding package workflow</h2>
            <span className={`status-pill ${packageStatus === "package_approved" ? "ready" : packageStatus === "rejected" ? "error" : "warn"}`}>
              {packageStatus.replaceAll("_", " ")}
            </span>
          </div>
          <div className="metric-row">
            <label className="summary-field">
              <span className="summary-field-label">Package status</span>
              <select className="text-input" value={packageStatus} onChange={(e) => setPackageStatus(e.target.value)}>
                {PACKAGE_STATUSES.map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}
              </select>
            </label>
            <label className="summary-field">
              <span className="summary-field-label">Package kind</span>
              <input className="text-input" value={packageKind} onChange={(e) => setPackageKind(e.target.value)} placeholder="existing_assessment_pack / generated_package" />
            </label>
            <label className="summary-field">
              <span className="summary-field-label">Package reference</span>
              <input className="text-input" value={packageRef} onChange={(e) => setPackageRef(e.target.value)} placeholder="fastapi_task_api_standard_v2" />
            </label>
          </div>
          <label className="summary-field">
            <span className="summary-field-label">Package notes</span>
            <textarea className="text-input" rows={3} value={packageNotes} onChange={(e) => setPackageNotes(e.target.value)} />
          </label>
          <div className="action-row">
            <button type="button" className="command-button secondary" onClick={() => reviewPackage("approve")} disabled={saving || !packageKind.trim() || !packageRef.trim()}>
              <CheckCircle2 size={16} aria-hidden="true" />
              Approve package
            </button>
            <button type="button" className="command-button secondary" onClick={() => reviewPackage("reject")} disabled={saving}>
              <XCircle size={16} aria-hidden="true" />
              Reject package
            </button>
          </div>
        </div>
      ) : null}

      <div className="summary-field">
        <span className="summary-field-label">Rubric dimensions</span>
        <p className="attempt-sent-at">{rubricDimensions}</p>
      </div>
      <div className="summary-field">
        <span className="summary-field-label">Expected evidence</span>
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          {question.expected_evidence.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </div>

      <label className="summary-field">
        <span className="summary-field-label">Review notes</span>
        <textarea className="text-input" rows={3} value={reviewNotes} disabled={question.status === "approved"} onChange={(e) => setReviewNotes(e.target.value)} />
      </label>

      {error ? <p className="submission-error">{error}</p> : null}

      <div className="action-row">
        {editable ? (
          <button type="button" className="command-button secondary" onClick={saveMetadata} disabled={saving}>
            {saving ? <Loader2 size={15} className="spin" aria-hidden="true" /> : <RefreshCw size={15} aria-hidden="true" />}
            Save metadata
          </button>
        ) : null}
        {question.status !== "approved" ? (
          <button type="button" className="command-button" onClick={() => review("approve")} disabled={saving}>
            <CheckCircle2 size={16} aria-hidden="true" />
            Approve
          </button>
        ) : null}
        {question.status === "needs_review" ? (
          <button type="button" className="command-button secondary" onClick={() => review("reject")} disabled={saving}>
            <XCircle size={16} aria-hidden="true" />
            Reject
          </button>
        ) : null}
        <button type="button" className="command-button secondary" onClick={deleteQuestion} disabled={saving}>
          <Trash2 size={16} aria-hidden="true" />
          Delete
        </button>
      </div>
    </article>
  );
}

export default function AdminQuestionBankPage() {
  const { getToken } = useAuth();
  const [questions, setQuestions] = useState<QuestionBankQuestion[]>([]);
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]>("needs_review");
  const [questionTypeFilter, setQuestionTypeFilter] = useState<(typeof QUESTION_TYPE_FILTERS)[number]>("all");
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [seedMessage, setSeedMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setQuestions(await fetchQuestionBankQuestions(statusFilter, getToken));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load question bank");
    } finally {
      setLoading(false);
    }
  }, [getToken, statusFilter]);

  useEffect(() => {
    let cancelled = false;
    void fetchQuestionBankQuestions(statusFilter, getToken)
      .then((items) => {
        if (!cancelled) setQuestions(items);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load question bank");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [getToken, statusFilter]);

  const stats = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const q of questions) {
      if (questionTypeFilter !== "all" && q.question_type !== questionTypeFilter) continue;
      counts[q.status] = (counts[q.status] ?? 0) + 1;
    }
    return counts;
  }, [questionTypeFilter, questions]);

  const visibleQuestions = useMemo(() => {
    if (questionTypeFilter === "all") return questions;
    return questions.filter((question) => question.question_type === questionTypeFilter);
  }, [questionTypeFilter, questions]);

  async function seedDrafts() {
    setSeeding(true);
    setError(null);
    setSeedMessage(null);
    try {
      const result = await seedQuestionBankDrafts(getToken);
      setSeedMessage(`Seeded ${result.created_questions} new questions across ${result.source_count} sources.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Seed failed");
    } finally {
      setSeeding(false);
    }
  }

  async function importSources() {
    setImporting(true);
    setError(null);
    setSeedMessage(null);
    try {
      const result = await importSourceQuestions(getToken);
      const suffix = result.errors.length ? ` ${result.errors.length} source files had errors.` : "";
      setSeedMessage(`Imported ${result.created_questions} new draft questions from ${result.fetched_sources} source files.${suffix}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Source import failed");
    } finally {
      setImporting(false);
    }
  }

  function replaceQuestion(updated: QuestionBankQuestion) {
    setQuestions((current) => current.map((item) => (item.id === updated.id ? updated : item)));
  }

  function removeQuestion(questionId: number) {
    setQuestions((current) => current.filter((item) => item.id !== questionId));
  }

  return (
    <main className="employer-page">
      <section className="employer-section" style={{ display: "grid", gap: 16 }}>
        <div className="section-title">
          <div>
            <h2>Question Bank</h2>
            <p className="attempt-sent-at">Review, edit, approve, or reject Phase 6A draft questions.</p>
          </div>
          <Link href="/admin" className="command-button secondary">Employers</Link>
        </div>

        <div className="action-row">
          <button type="button" className="command-button" onClick={seedDrafts} disabled={seeding}>
            {seeding ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <Database size={16} aria-hidden="true" />}
            Seed draft questions
          </button>
          <button type="button" className="command-button secondary" onClick={importSources} disabled={importing}>
            {importing ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <Database size={16} aria-hidden="true" />}
            Import source questions
          </button>
          <button type="button" className="command-button secondary" onClick={refresh} disabled={loading}>
            <RefreshCw size={16} aria-hidden="true" />
            Refresh
          </button>
        </div>

        <div className="seg full" role="group" aria-label="Question status filter">
          {STATUS_FILTERS.map((status) => (
            <button
              key={status}
              type="button"
              className={statusFilter === status ? "active" : undefined}
              onClick={() => {
                setLoading(true);
                setError(null);
                setStatusFilter(status);
              }}
            >
              {status.replaceAll("_", " ")}
            </button>
          ))}
        </div>

        <label className="summary-field">
          <span className="summary-field-label">Question type filter</span>
          <select
            className="text-input"
            value={questionTypeFilter}
            onChange={(event) => setQuestionTypeFilter(event.target.value as (typeof QUESTION_TYPE_FILTERS)[number])}
          >
            {QUESTION_TYPE_FILTERS.map((item) => (
              <option key={item} value={item}>{item.replaceAll("_", " ")}</option>
            ))}
          </select>
        </label>

        {seedMessage ? <p className="submission-success">{seedMessage}</p> : null}
        {error ? <p className="submission-error">{error}</p> : null}
        {loading ? <p className="empty-state"><Loader2 size={16} className="spin" aria-hidden="true" /> Loading question bank…</p> : null}

        <div className="metric-row">
          <div className="metric"><span>Visible questions</span><strong>{visibleQuestions.length}</strong></div>
          <div className="metric"><span>Needs review</span><strong>{stats.needs_review ?? 0}</strong></div>
          <div className="metric"><span>Approved</span><strong>{stats.approved ?? 0}</strong></div>
          <div className="metric"><span>Rejected</span><strong>{stats.rejected ?? 0}</strong></div>
        </div>
      </section>

      <div style={{ display: "grid", gap: 16, marginTop: 16 }}>
        {visibleQuestions.map((question) => (
          <QuestionReviewCard key={question.id} question={question} onSaved={replaceQuestion} onDeleted={removeQuestion} />
        ))}
        {!visibleQuestions.length && !loading ? (
          <p className="empty-state">No questions in this filter. Seed drafts or switch filters.</p>
        ) : null}
      </div>
    </main>
  );
}
