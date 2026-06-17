"use client";

import { ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ApiError, fetchReport, generateReport } from "../../api";
import type { EvidenceReportResponse } from "../../types";

function recommendationLabel(value: string | null): string {
  if (!value) return "No recommendation";
  return value.replaceAll("_", " ");
}

function recommendationClass(value: string | null): string {
  if (!value) return "";
  if (value === "strong_advance") return "ready";
  if (value === "advance_with_followups") return "warn";
  if (value === "needs_review") return "warn";
  return "fail";
}

function SectionTitle({ title }: { title: string }) {
  return (
    <div className="section-title">
      <h2>{title}</h2>
    </div>
  );
}

function JsonBlock({ value }: { value: unknown }) {
  return <pre className="report-json">{JSON.stringify(value, null, 2)}</pre>;
}

export default function ReportDetail() {
  const params = useParams<{ attemptId: string | string[] }>();
  const attemptIdParam = params.attemptId;
  const attemptId = Array.isArray(attemptIdParam) ? attemptIdParam[0] : attemptIdParam;
  const [report, setReport] = useState<EvidenceReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setReport(await fetchReport(attemptId));
    } catch (loadError) {
      if (loadError instanceof ApiError && loadError.status === 404) {
        try {
          setReport(await generateReport(attemptId));
        } catch (generateError) {
          setError(generateError instanceof Error ? generateError.message : "Report generation failed");
        }
      } else {
        setError(loadError instanceof Error ? loadError.message : "Report load failed");
      }
    } finally {
      setLoading(false);
    }
  }, [attemptId]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadReport();
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [loadReport]);

  async function createReport() {
    setGenerating(true);
    setError(null);
    try {
      setReport(await generateReport(attemptId));
    } catch (generateError) {
      setError(generateError instanceof Error ? generateError.message : "Report generation failed");
    } finally {
      setGenerating(false);
    }
  }

  const r = report?.report;

  return (
    <main className="employer-page">
      <header className="employer-header">
        <div>
          <Link className="back-link" href="/employer">
            <ArrowLeft size={16} aria-hidden="true" />
            Back to attempts
          </Link>
          <h1>Evidence Report</h1>
          <p>Attempt #{attemptId}</p>
        </div>
        <div className="topbar-actions">
          <button className="command-button secondary" disabled={loading} onClick={loadReport}>
            <RefreshCw size={17} aria-hidden="true" />
            Refresh
          </button>
          <button className="command-button primary" disabled={generating} onClick={createReport}>
            <RefreshCw size={17} aria-hidden="true" />
            {generating ? "Generating" : "Regenerate"}
          </button>
        </div>
      </header>

      {loading ? <p className="empty-state">Loading or generating report…</p> : null}
      {error ? <p className="submission-error">{error}</p> : null}

      {r ? (
        <>
          {/* Top metrics */}
          <section className="metric-row">
            <div className="metric">
              <span>Score</span>
              <strong>{report?.score_total ?? "-"} / 100</strong>
            </div>
            <div className="metric">
              <span>Recommendation</span>
              <strong className={`status-pill ${recommendationClass(report?.recommendation ?? null)}`}>
                {recommendationLabel(report?.recommendation ?? null)}
              </strong>
            </div>
            <div className="metric">
              <span>Confidence</span>
              <strong>{r.scores.confidence}</strong>
            </div>
          </section>

          {/* Executive summary */}
          <section className="employer-section">
            <SectionTitle title="Executive summary" />
            <p className="report-copy">{r.executive_summary.summary}</p>
            {r.executive_summary.evidence_limits?.length ? (
              <ul className="report-notes">
                {r.executive_summary.evidence_limits.map((note: string) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            ) : null}
          </section>

          {/* Score breakdown */}
          <section className="employer-section">
            <SectionTitle title="Score breakdown" />
            <div className="score-list">
              {r.scores.categories.map((cat: { category: string; points: number; max_points: number; evidence: string }) => (
                <div className="score-row" key={cat.category}>
                  <div>
                    <strong>{cat.category}</strong>
                    <p>{cat.evidence}</p>
                  </div>
                  <span>{cat.points}/{cat.max_points}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Public + hidden test results */}
          <section className="report-grid">
            <article className="employer-section">
              <SectionTitle title="Public test results" />
              <p className="report-copy">
                Ran {r.public_test_results.run_count} time(s). Last run: {r.public_test_results.last_run_summary.status} —{" "}
                {r.public_test_results.last_run_summary.passed}/{r.public_test_results.last_run_summary.collected} passed.
              </p>
              {r.public_test_results.last_run_summary.failure_names?.length ? (
                <>
                  <p className="report-label">Failures:</p>
                  <ul className="report-list">
                    {r.public_test_results.last_run_summary.failure_names.map((name: string) => (
                      <li key={name}>{name}</li>
                    ))}
                  </ul>
                </>
              ) : null}
              <p className="report-label">Initially failing (count toward score):</p>
              <ul className="report-list">
                {r.public_test_results.initially_failing_tests.map((name: string) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
            </article>

            <article className="employer-section">
              <SectionTitle title="Hidden test results" />
              <p className="report-copy">
                Status: {r.hidden_test_results.summary.status} —{" "}
                {r.hidden_test_results.summary.passed}/{r.hidden_test_results.summary.collected} passed.
              </p>
              {r.hidden_test_results.summary.failure_names?.length ? (
                <>
                  <p className="report-label">Failures:</p>
                  <ul className="report-list">
                    {r.hidden_test_results.summary.failure_names.map((name: string) => (
                      <li key={name}>{name}</li>
                    ))}
                  </ul>
                </>
              ) : null}
              <p className="report-label">Seeded issue areas:</p>
              <ul className="report-list">
                {r.hidden_test_results.seeded_issue_areas.map((area: string) => (
                  <li key={area}>{area}</li>
                ))}
              </ul>
            </article>
          </section>

          {/* Candidate tests + AI collaboration */}
          <section className="report-grid">
            <article className="employer-section">
              <SectionTitle title="Candidate-written tests" />
              <p className="report-copy">{r.candidate_tests.candidate_test_file_count} test file(s) added or modified.</p>
              {r.candidate_tests.added_test_files?.length ? (
                <>
                  <p className="report-label">Added:</p>
                  <ul className="report-list">
                    {r.candidate_tests.added_test_files.map((f: string) => <li key={f}>{f}</li>)}
                  </ul>
                </>
              ) : null}
              {r.candidate_tests.modified_test_files?.length ? (
                <>
                  <p className="report-label">Modified:</p>
                  <ul className="report-list">
                    {r.candidate_tests.modified_test_files.map((f: string) => <li key={f}>{f}</li>)}
                  </ul>
                </>
              ) : null}
            </article>

            <article className="employer-section">
              <SectionTitle title="AI collaboration" />
              <p className="report-copy">
                {r.ai_collaboration.candidate_prompt_count} candidate prompt(s),{" "}
                {r.ai_collaboration.policy_redirect_count} policy redirect(s).
              </p>
              {r.ai_collaboration.flagged_prompts?.length ? (
                <>
                  <p className="report-label">Flagged prompts:</p>
                  <ul className="report-list">
                    {r.ai_collaboration.flagged_prompts.map((fp: { message: string; policy_tags: string[]; at: string }) => (
                      <li key={fp.at}>
                        <em>{fp.policy_tags.join(", ")}</em> — {fp.message}
                      </li>
                    ))}
                  </ul>
                </>
              ) : null}
              {r.ai_collaboration.pasted_ai_code?.pasted_ai_code_count > 0 ? (
                <p className="report-copy report-warn">
                  ⚠ {r.ai_collaboration.pasted_ai_code.pasted_ai_code_count} AI code block(s) found verbatim in final submission.
                </p>
              ) : null}
              {r.ai_collaboration.large_paste_events?.large_paste_count > 0 ? (
                <p className="report-copy report-warn">
                  ⚠ {r.ai_collaboration.large_paste_events.large_paste_count} large paste event(s) detected between snapshots.
                </p>
              ) : null}
            </article>
          </section>

          {/* Explanation + process evidence */}
          <section className="report-grid">
            <article className="employer-section">
              <SectionTitle title="Explanation submitted" />
              <p className="report-label">Final explanation:</p>
              <p className="report-copy">{r.explanation_submitted.final_explanation || "—"}</p>
              <p className="report-label">Decision log:</p>
              <p className="report-copy">{r.explanation_submitted.decision_log || "—"}</p>
            </article>

            <article className="employer-section">
              <SectionTitle title="Process evidence" />
              <p className="report-copy">
                {r.process_evidence.snapshot_count} snapshot(s), {r.process_evidence.test_run_count} test run(s).
              </p>
              {r.process_evidence.test_runs?.length ? (
                <ul className="report-list">
                  {r.process_evidence.test_runs.map((run: { id: number; type: string; status: string; duration_ms: number }) => (
                    <li key={run.id}>
                      {run.type} — {run.status} ({run.duration_ms}ms)
                    </li>
                  ))}
                </ul>
              ) : null}
            </article>
          </section>

          {/* Follow-up questions */}
          <section className="employer-section">
            <SectionTitle title="Suggested follow-up questions" />
            <ol className="question-list">
              {r.follow_up_questions.map((q: string) => (
                <li key={q}>{q}</li>
              ))}
            </ol>
          </section>

          {/* Timeline */}
          <section className="employer-section">
            <SectionTitle title="Timeline" />
            <ul className="report-list timeline-list">
              {r.timeline.map((event: { at: string; type: string; summary: string }) => (
                <li key={`${event.at}-${event.type}`}>
                  <span className="timeline-time">{new Date(event.at).toLocaleTimeString()}</span>
                  <span className="timeline-type">{event.type}</span>
                  <span>{event.summary}</span>
                </li>
              ))}
            </ul>
          </section>
        </>
      ) : null}
    </main>
  );
}
