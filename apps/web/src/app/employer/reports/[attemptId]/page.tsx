"use client";

import { useAuth } from "@clerk/nextjs";
import { ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { ReactNode } from "react";
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

function Disclosure({ label, children }: { label: string; children: ReactNode }) {
  return (
    <details className="report-disclosure">
      <summary>{label}</summary>
      <div className="report-disclosure-body">{children}</div>
    </details>
  );
}

function FileViewer({ files }: { files: Record<string, string> }) {
  const paths = Object.keys(files);
  const defaultOpen = paths.find((p) => p.startsWith("task_api/")) ?? paths[0] ?? null;
  const [openFile, setOpenFile] = useState<string | null>(defaultOpen);

  if (!paths.length) return <p className="report-copy">No files submitted.</p>;

  return (
    <div className="file-viewer">
      <div className="file-viewer-list">
        {paths.map((path) => (
          <button
            key={path}
            className={`file-viewer-tab${openFile === path ? " active" : ""}`}
            onClick={() => setOpenFile(openFile === path ? null : path)}
          >
            {path}
          </button>
        ))}
      </div>
      {openFile && files[openFile] !== undefined ? (
        <pre className="file-viewer-content"><code>{files[openFile]}</code></pre>
      ) : null}
    </div>
  );
}

function percentage(points: number, maxPoints: number): number {
  if (!maxPoints) return 0;
  return Math.max(0, Math.min(100, Math.round((points / maxPoints) * 100)));
}

function barColorClass(pct: number): string {
  if (pct >= 70) return "good";
  if (pct >= 40) return "warn";
  return "danger";
}

function ChartBar({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = percentage(value, max);
  return (
    <div className="chart-bar">
      <div className="chart-bar-label">
        <span>{label}</span>
        <strong>{value}/{max}</strong>
      </div>
      <div className={`chart-track ${barColorClass(pct)}`} aria-hidden="true">
        <span style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function TestResultBar({ label, passed, collected }: { label: string; passed: number; collected: number }) {
  return <ChartBar label={label} value={passed} max={collected || 1} />;
}

function ScoreRing({ score, max }: { score: number; max: number }) {
  const pct = Math.max(0, Math.min(1, score / max));
  const r = 38;
  const circ = 2 * Math.PI * r;
  const dash = pct * circ;
  const color = pct >= 0.7 ? "#0f766e" : pct >= 0.4 ? "#d97706" : "#dc2626";
  return (
    <svg width="96" height="96" viewBox="0 0 96 96" aria-hidden="true">
      <circle cx="48" cy="48" r={r} fill="none" stroke="#e8edf3" strokeWidth="10" />
      <circle
        cx="48" cy="48" r={r} fill="none" stroke={color} strokeWidth="10"
        strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
        transform="rotate(-90 48 48)"
      />
      <text x="48" y="44" textAnchor="middle" fontSize="22" fontWeight="700" fill="#18212f">{score}</text>
      <text x="48" y="62" textAnchor="middle" fontSize="12" fill="#607083">/ {max}</text>
    </svg>
  );
}

function formatTimingValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return `${value}m`;
  return String(value);
}

function formatMs(value: number | undefined): string {
  if (value === undefined) return "-";
  if (value >= 1000) return `${(value / 1000).toFixed(1)}s`;
  return `${value}ms`;
}

export default function ReportDetail() {
  const params = useParams<{ attemptId: string | string[] }>();
  const attemptIdParam = params.attemptId;
  const attemptId = Array.isArray(attemptIdParam) ? attemptIdParam[0] : attemptIdParam;
  const { getToken, isLoaded } = useAuth();
  const [report, setReport] = useState<EvidenceReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setReport(await fetchReport(attemptId, getToken));
    } catch (loadError) {
      if (loadError instanceof ApiError && loadError.status === 404) {
        try {
          setReport(await generateReport(attemptId, getToken));
        } catch (generateError) {
          setError(generateError instanceof Error ? generateError.message : "Report generation failed");
        }
      } else {
        setError(loadError instanceof Error ? loadError.message : "Report load failed");
      }
    } finally {
      setLoading(false);
    }
  }, [attemptId, getToken]);

  useEffect(() => {
    if (!isLoaded) return;
    const timeoutId = window.setTimeout(() => {
      void loadReport();
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [loadReport, isLoaded]);

  async function createReport() {
    setGenerating(true);
    setError(null);
    try {
      setReport(await generateReport(attemptId, getToken));
    } catch (generateError) {
      setError(generateError instanceof Error ? generateError.message : "Report generation failed");
    } finally {
      setGenerating(false);
    }
  }

  const r = report?.report;
  const timing = r?.metadata?.timing;
  const featureScore = r?.feature_design_implementation
    ?? r?.scores?.categories?.find((cat: { category: string }) => cat.category === "Feature/design implementation");

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
          {/* Recommendation banner */}
          <div className={`recommendation-banner ${recommendationClass(report?.recommendation ?? null)}`}>
            <ScoreRing score={report?.score_total ?? 0} max={100} />
            <div>
              <p className="rec-label">Recommendation</p>
              <p className="rec-value">{recommendationLabel(report?.recommendation ?? null)}</p>
              <p className="rec-label" style={{ marginTop: 6 }}>Assessment: {r.metadata.assessment.version}</p>
            </div>
          </div>

          {/* Top metrics */}
          <section className="metric-row">
            <div className="metric">
              <span>Timing</span>
              <strong>{timing?.timing_mode ?? "untimed"}</strong>
            </div>
            <div className="metric">
              {timing?.timing_mode === "untimed" ? (
                <>
                  <span>Time used</span>
                  <strong>{formatTimingValue(timing?.time_used_minutes)}</strong>
                </>
              ) : (
                <>
                  <span>Duration / used</span>
                  <strong>{formatTimingValue(timing?.duration_minutes)} / {formatTimingValue(timing?.time_used_minutes)}</strong>
                </>
              )}
            </div>
            <div className="metric">
              <span>Submission</span>
              <strong>{timing?.submission_mode === "auto_expired" ? "Auto (expired)" : "Manual"}</strong>
            </div>
            <div className="metric">
              <span>Evaluator mode</span>
              <strong>{r.metadata.evaluator_feedback_mode ?? "strict"}</strong>
            </div>
          </section>

          {/* Executive summary */}
          <section className="employer-section">
            <SectionTitle title="Executive summary" />
            <p className="report-copy">{r.executive_summary.summary}</p>
            {r.executive_summary.evidence_limits?.length ? (
              <Disclosure label="Evidence limits">
                <ul className="report-list">
                  {r.executive_summary.evidence_limits.map((note: string) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </Disclosure>
            ) : null}
          </section>

          {/* Score breakdown */}
          <section className="employer-section">
            <SectionTitle title="Score breakdown" />
            <div className="chart-list">
              {r.scores.categories.map((cat: { category: string; points: number; max_points: number }) => (
                <ChartBar key={cat.category} label={cat.category} value={cat.points} max={cat.max_points} />
              ))}
            </div>
            <div className="score-list">
              {r.scores.categories.map((cat: { category: string; points: number; max_points: number; evidence: string }) => {
                const sectionId: Record<string, string> = {
                  public_issue_resolution: "section-public-tests",
                  private_issue_generalization: "section-hidden-tests",
                  feature_design_implementation: "section-feature-design",
                  candidate_tests: "section-candidate-tests",
                  ai_collaboration: "section-ai-collaboration",
                  regression_code_quality: "section-public-tests",
                };
                const anchor = sectionId[cat.category];
                return (
                  <div className="score-row" key={cat.category}>
                    <div>
                      <strong>
                        {anchor ? (
                          <a href={`#${anchor}`} className="score-row-link">{cat.category}</a>
                        ) : cat.category}
                      </strong>
                      <p>{cat.evidence}</p>
                    </div>
                    <span>{cat.points}/{cat.max_points}</span>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Test results */}
          <section className="report-grid">
            <article id="section-public-tests" className="employer-section">
              <SectionTitle title="Public tests" />
              <TestResultBar
                label="Public tests"
                passed={r.public_test_results.last_run_summary.passed}
                collected={r.public_test_results.last_run_summary.collected}
              />
              <p className="report-copy">
                {r.public_test_results.last_run_summary.passed}/{r.public_test_results.last_run_summary.collected} passed
                · ran {r.public_test_results.run_count} time(s)
              </p>
              {r.public_test_results.last_run_summary.failure_names?.length ? (
                <Disclosure label={`${r.public_test_results.last_run_summary.failure_names.length} failure(s)`}>
                  <ul className="report-list">
                    {r.public_test_results.last_run_summary.failure_names.map((name: string) => (
                      <li key={name}>{name}</li>
                    ))}
                  </ul>
                </Disclosure>
              ) : null}
              {r.public_test_results.initially_failing_tests?.length ? (
                <Disclosure label="Initially failing tests">
                  <ul className="report-list">
                    {r.public_test_results.initially_failing_tests.map((name: string) => (
                      <li key={name}>{name}</li>
                    ))}
                  </ul>
                </Disclosure>
              ) : null}
            </article>

            <article id="section-hidden-tests" className="employer-section">
              <SectionTitle title="Hidden tests" />
              <TestResultBar
                label="Hidden tests"
                passed={r.hidden_test_results.summary.passed}
                collected={r.hidden_test_results.summary.collected}
              />
              <p className="report-copy">
                {r.hidden_test_results.summary.passed}/{r.hidden_test_results.summary.collected} passed
              </p>
              {r.hidden_test_results.summary.failure_names?.length ? (
                <Disclosure label={`${r.hidden_test_results.summary.failure_names.length} failure(s)`}>
                  <ul className="report-list">
                    {r.hidden_test_results.summary.failure_names.map((name: string) => (
                      <li key={name}>{name}</li>
                    ))}
                  </ul>
                </Disclosure>
              ) : null}
              <Disclosure label="Seeded issue areas">
                <ul className="report-list">
                  {r.hidden_test_results.seeded_issue_areas.map((area: string) => (
                    <li key={area}>{area}</li>
                  ))}
                </ul>
              </Disclosure>
            </article>
          </section>

          {/* Feature/design + FAVO */}
          <section className="report-grid">
            <article id="section-feature-design" className="employer-section">
              <SectionTitle title="Feature/design implementation" />
              <p className="report-copy">
                {featureScore ? `${featureScore.points}/${featureScore.max_points}: ${featureScore.evidence}` : "No feature/design score available."}
              </p>
            </article>

            <article className="employer-section">
              <SectionTitle title="FAVO interpretation" />
              <div className="favo-grid">
                {(["frame", "ask", "verify", "own"] as const).map((key) => {
                  const favoLabels: Record<string, string> = { frame: "Frame", ask: "Ask", verify: "Verify", own: "Own" };
                  const value = r.favo[key] as { label: string; evidence: string } | undefined;
                  if (!value) return null;
                  return (
                    <span key={key}>
                      <strong>{favoLabels[key]}</strong>
                      <em>{value.label}</em>
                      {value.evidence}
                    </span>
                  );
                })}
              </div>
            </article>
          </section>

          {/* Candidate tests + AI */}
          <section className="report-grid">
            <article id="section-candidate-tests" className="employer-section">
              <SectionTitle title="Candidate-written tests" />
              <p className="report-copy">
                {(() => {
                  const added = r.candidate_tests.functions_added ?? r.candidate_tests.candidate_test_function_count ?? 0;
                  const modified = r.candidate_tests.functions_modified ?? 0;
                  if (added === 0 && modified === 0) return "No candidate-written test functions detected.";
                  const parts = [];
                  if (added > 0) parts.push(`${added} function${added === 1 ? "" : "s"} added`);
                  if (modified > 0) parts.push(`${modified} modified`);
                  return parts.join(" · ");
                })()}
              </p>
              {(r.candidate_tests.added_test_files?.length || r.candidate_tests.modified_test_files?.length) ? (
                <Disclosure label="Files changed">
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
                </Disclosure>
              ) : null}
            </article>

            <article id="section-ai-collaboration" className="employer-section">
              <SectionTitle title="AI collaboration" />
              <p className="report-copy">
                {r.ai_collaboration.candidate_prompt_count} prompt(s)
                · {r.ai_collaboration.policy_redirect_count} redirect(s)
                · integrity risk: <span className={r.ai_integrity_risk.label === "low" ? "" : "report-warn"}>{r.ai_integrity_risk.label}</span>
              </p>
              {r.ai_collaboration.pasted_ai_code?.pasted_ai_code_count > 0 ? (
                <p className="report-copy report-warn">
                  ⚠ {r.ai_collaboration.pasted_ai_code.pasted_ai_code_count} AI code block(s) found verbatim in submission.
                </p>
              ) : null}
              {r.ai_collaboration.large_paste_events?.large_paste_count > 0 ? (
                <p className="report-copy report-warn">
                  ⚠ {r.ai_collaboration.large_paste_events.large_paste_count} large paste event(s) detected.
                </p>
              ) : null}
              {r.ai_collaboration.flagged_prompts?.length ? (
                <Disclosure label={`${r.ai_collaboration.flagged_prompts.length} flagged prompt(s)`}>
                  <ul className="report-list">
                    {r.ai_collaboration.flagged_prompts.map((fp: { message: string; policy_tags: string[]; at: string }) => (
                      <li key={fp.at}>
                        <em>{fp.policy_tags.join(", ")}</em> — {fp.message}
                      </li>
                    ))}
                  </ul>
                </Disclosure>
              ) : null}
              <Disclosure label="Integrity signals">
                <ul className="report-list">
                  {Object.entries(r.ai_integrity_risk.signals).map(([name, value]) => (
                    <li key={name}>{name}: {String(value)}</li>
                  ))}
                </ul>
              </Disclosure>
            </article>
          </section>

          {/* Submission review */}
          <section className="employer-section">
            <SectionTitle title="Submission review" />
            {(() => {
              const sr = r.submission_review;
              const entries: { label: string; value: string }[] = [
                { label: "What changed", value: sr.what_changed || "" },
                { label: "Tradeoffs / decisions", value: sr.tradeoffs_or_product_decisions || "" },
                { label: "Verification", value: sr.verification || "" },
                { label: "Given more time", value: sr.improvements_with_more_time || "" },
                { label: "Notes", value: sr.additional_notes || "" },
              ].filter((e) => e.value.trim().length > 0);
              if (entries.length === 0) {
                return <p className="report-copy report-muted">No submission notes provided.</p>;
              }
              return (
                <div className="report-grid">
                  {entries.map((e) => (
                    <article key={e.label}>
                      <p className="report-label">{e.label}</p>
                      <p className="report-copy">{e.value}</p>
                    </article>
                  ))}
                </div>
              );
            })()}
          </section>

          {/* Submitted code */}
          {r.submitted_code?.files ? (
            <section className="employer-section">
              <SectionTitle title="Submitted code" />
              <p className="report-copy report-muted">{r.submitted_code.file_count} file(s) submitted.</p>
              <FileViewer files={r.submitted_code.files} />
            </section>
          ) : null}

          {/* Follow-up questions */}
          <section className="employer-section">
            <SectionTitle title="Suggested follow-up questions" />
            <ol className="question-list">
              {r.follow_up_questions.map((q: string) => (
                <li key={q}>{q}</li>
              ))}
            </ol>
          </section>

          {/* Process evidence + Timeline — collapsed by default */}
          <section className="report-grid">
            <article className="employer-section">
              <SectionTitle title="Process evidence" />
              <p className="report-copy">
                {r.process_evidence.snapshot_count} snapshot(s) · {r.process_evidence.test_run_count} test run(s)
              </p>
              {r.process_evidence.test_runs?.length ? (
                <Disclosure label="Test run details">
                  <ul className="report-list">
                    {r.process_evidence.test_runs.map((run: { id: number; type: string; status: string; duration_ms: number; timings?: Record<string, number> }) => (
                      <li key={run.id}>
                        {run.type} — {run.status}
                        {run.timings && Object.keys(run.timings).length ? (
                          <span className="report-muted">
                            {" "}· {formatMs(run.timings.api_total_ms ?? run.timings.worker_total_ms)}
                            {run.timings.worker_pytest_ms !== undefined ? ` · pytest ${formatMs(run.timings.worker_pytest_ms)}` : ""}
                          </span>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </Disclosure>
              ) : null}
            </article>

            <article className="employer-section">
              <SectionTitle title="Timeline" />
              <p className="report-copy">{r.timeline.length} event(s)</p>
              <Disclosure label="Show timeline">
                <ul className="report-list timeline-list">
                  {r.timeline.map((event: { at: string; type: string; summary: string }) => (
                    <li key={`${event.at}-${event.type}`}>
                      <span className="timeline-time">{new Date(event.at).toLocaleTimeString()}</span>
                      <span className="timeline-type">{event.type}</span>
                      <span>{event.summary}</span>
                    </li>
                  ))}
                </ul>
              </Disclosure>
            </article>
          </section>
        </>
      ) : null}
    </main>
  );
}
