"use client";

import { useAuth } from "@clerk/nextjs";
import { ArrowLeft, Loader2, RotateCw } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { ReactNode } from "react";
import { useCallback, useEffect, useState } from "react";

import { fetchAdminReport } from "../../api";
import type { AdminEvidenceReport } from "../../types";
import type { EvidenceReportResponse } from "../../../employer/types";

const Logo = () => (
  <svg className="topbar-logo" width="30" height="30" viewBox="0 0 30 30" fill="none" aria-label="SignalLoop">
    <rect width="30" height="30" rx="7" fill="#0f766e" />
    <path d="M15 6C19.97 6 24 10.03 24 15C24 19.97 19.97 24 15 24C10.5 24 6.8 20.7 6.1 16.4" stroke="white" strokeWidth="2.3" strokeLinecap="round" />
    <path d="M4.5 14.5L6.2 17.2L9 15.5" stroke="white" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="15" cy="6" r="2" fill="#5eead4" />
  </svg>
);

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

function riskClass(label: string): string {
  if (label === "critical" || label === "high") return "error";
  if (label === "medium") return "warn";
  return "";
}

function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="section-title">
      <div>
        <h2>{title}</h2>
        {subtitle ? <p className="report-section-subtitle">{subtitle}</p> : null}
      </div>
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

function ChartBar({ label, value, max, anchor }: { label: string; value: number; max: number; anchor?: string }) {
  const pct = percentage(value, max);
  return (
    <div className="chart-bar">
      <div className="chart-bar-label">
        <span>
          {anchor ? (
            <a href={`#${anchor}`} className="chart-bar-link">{label}</a>
          ) : label}
        </span>
        <strong>{value}/{max}</strong>
      </div>
      <div className={`chart-track ${barColorClass(pct)}`} aria-hidden="true">
        <span style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
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

const SECTION_ANCHORS: Record<string, string> = {
  public_issue_resolution: "section-public-tests",
  private_issue_generalization: "section-hidden-tests",
  feature_design_implementation: "section-enhancements",
  candidate_tests: "section-candidate-tests",
  ai_collaboration: "section-ai-collaboration",
};

const CATEGORY_LABELS: Record<string, string> = {
  public_issue_resolution: "Public tests",
  private_issue_generalization: "Hidden tests",
  feature_design_implementation: "Enhancements",
  candidate_tests: "Candidate tests",
  ai_collaboration: "AI collaboration",
  regression_code_quality: "Regression",
};

function formatDuration(totalSeconds: number): string {
  if (totalSeconds <= 0) return "0s";
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  if (m === 0) return `${s}s`;
  if (s === 0) return `${m}m`;
  return `${m}m ${s}s`;
}

function formatElapsed(startedAt: string | null | undefined, eventAt: string | null): string {
  if (!startedAt || !eventAt) return "—";
  const secs = Math.round((new Date(eventAt).getTime() - new Date(startedAt).getTime()) / 1000);
  if (secs < 0) return "—";
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  return [h, m, s].map((v) => String(v).padStart(2, "0")).join(":");
}

function buildIntegrityFactorSummary(factors: Array<{ signal: string; value: number; weight: string }>): string {
  const parts: string[] = [];
  for (const f of factors) {
    if (f.weight === "none" || f.value === 0) continue;
    if (f.signal === "focus_loss_count") parts.push(`${f.value} focus-loss event${f.value !== 1 ? "s" : ""}`);
    else if (f.signal === "fullscreen_exits") parts.push(`${f.value} fullscreen exit${f.value !== 1 ? "s" : ""}`);
    else if (f.signal === "large_paste_count") parts.push(`${f.value} large paste${f.value !== 1 ? "s" : ""}`);
    else if (f.signal === "ai_violation_count") parts.push(`${f.value} AI policy violation${f.value !== 1 ? "s" : ""}`);
    else if (f.signal === "prompt_injection_count" && f.value > 0) parts.push(`${f.value} prompt injection attempt${f.value !== 1 ? "s" : ""}`);
  }
  return parts.join(", ");
}

function IntegrityBanner({ integrityScore, aiRisk }: {
  integrityScore?: { label: string; contributing_factors: Array<{ signal: string; value: number; weight: string }> } | null;
  aiRisk?: { label: string } | null;
}) {
  const label = integrityScore?.label ?? aiRisk?.label ?? "low";
  if (label === "low") return null;
  if (label === "medium") {
    return (
      <div className="integrity-banner warn">
        ⚠ Moderate integrity signals — see Proctoring Signals and AI collaboration sections.
      </div>
    );
  }
  const summary = integrityScore ? buildIntegrityFactorSummary(integrityScore.contributing_factors) : "";
  return (
    <div className="integrity-banner error">
      ⚠ High integrity risk{summary ? ` — ${summary}` : ""}. Review proctoring signals and AI collaboration evidence carefully before advancing this candidate.
    </div>
  );
}

function formatMs(value: number | undefined): string {
  if (value === undefined) return "—";
  if (value >= 1000) return `${(value / 1000).toFixed(1)}s`;
  return `${value}ms`;
}

function ProctoringSignalsSection({ signals, startedAt }: {
  signals?: { webcam_consented: boolean | null; focus_loss_count: number; focus_loss_duration_seconds: number; fullscreen_exit_count: number; large_paste_count: number; focus_events: Array<{ occurred_at: string | null; duration_seconds: number }>; snapshots: Array<{ timestamp: string | null; trigger: string; url: string }> } | null;
  startedAt?: string | null;
}) {
  if (!signals) {
    return (
      <section className="employer-section">
        <SectionTitle title="Proctoring Signals" />
        <p className="report-copy report-muted">No proctoring data available for this attempt.</p>
      </section>
    );
  }

  const webcamLabel = signals.webcam_consented === true
    ? "Webcam enabled"
    : signals.webcam_consented === false
    ? "Webcam declined"
    : "Webcam not requested";
  const webcamClass = signals.webcam_consented === true ? "ready" : "";

  return (
    <section className="employer-section">
      <SectionTitle title="Proctoring Signals" />
      <div style={{ marginBottom: 12 }}>
        <span className={`status-pill ${webcamClass}`}>{webcamLabel}</span>
      </div>
      <table className="proctoring-table">
        <tbody>
          <tr><td>Focus-loss events</td><td><strong>{signals.focus_loss_count}</strong></td></tr>
          <tr><td>Total time away</td><td><strong>{formatDuration(signals.focus_loss_duration_seconds)}</strong></td></tr>
          <tr><td>Fullscreen exits</td><td><strong>{signals.fullscreen_exit_count}</strong></td></tr>
          <tr><td>Large pastes</td><td><strong>{signals.large_paste_count}</strong></td></tr>
        </tbody>
      </table>
      {signals.focus_events.length > 0 ? (
        <details className="report-disclosure" style={{ marginTop: 12 }}>
          <summary>Focus-loss timeline ({signals.focus_events.length} events)</summary>
          <div className="report-disclosure-body">
            <ul className="report-list">
              {signals.focus_events.map((ev, i) => (
                <li key={i}>
                  {formatElapsed(startedAt, ev.occurred_at)} elapsed — away for {formatDuration(ev.duration_seconds)}
                </li>
              ))}
            </ul>
          </div>
        </details>
      ) : null}
      {signals.webcam_consented === true ? (
        signals.snapshots.length > 0 ? (
          <div className="snapshot-strip" style={{ marginTop: 12 }}>
            {signals.snapshots.map((snap, i) => (
              <a key={i} href={snap.url} target="_blank" rel="noreferrer" className="snapshot-thumb-link" title={`${snap.trigger} · ${formatElapsed(startedAt, snap.timestamp)}`}>
                <img src={snap.url} alt={`Snapshot at ${formatElapsed(startedAt, snap.timestamp)}`} className="snapshot-thumb" />
                <span className="snapshot-thumb-label">{formatElapsed(startedAt, snap.timestamp)}</span>
              </a>
            ))}
          </div>
        ) : (
          <p className="report-copy report-muted" style={{ marginTop: 8 }}>No snapshots captured.</p>
        )
      ) : (
        <p className="report-copy report-muted" style={{ marginTop: 8 }}>Candidate did not enable webcam for this assessment.</p>
      )}
    </section>
  );
}

export default function AdminReportDetail() {
  const params = useParams<{ attemptId: string | string[] }>();
  const attemptIdParam = params.attemptId;
  const attemptId = Array.isArray(attemptIdParam) ? attemptIdParam[0] : attemptIdParam;
  const { getToken, isLoaded } = useAuth();
  const [adminReport, setAdminReport] = useState<AdminEvidenceReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setAdminReport(await fetchAdminReport(attemptId, getToken));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Report load failed");
    } finally {
      setLoading(false);
    }
  }, [attemptId, getToken]);

  useEffect(() => {
    if (!isLoaded) return;
    const timeoutId = window.setTimeout(() => void loadReport(), 0);
    return () => window.clearTimeout(timeoutId);
  }, [loadReport, isLoaded]);

  const report = adminReport as unknown as EvidenceReportResponse | null;
  const r = report?.report;

  return (
    <main className="employer-page">
      <header className="employer-header">
        <div className="report-header-brand">
          <Logo />
          <div>
            <Link className="back-link" href="/admin">
              <ArrowLeft size={16} aria-hidden="true" />
              Back to admin
            </Link>
            <h1>Evidence Report</h1>
            <p>
              {r?.metadata?.candidate_email ?? `Attempt #${attemptId}`}
              {r?.metadata?.assessment ? ` · ${r.metadata.assessment.title ?? r.metadata.assessment.version}` : ""}
            </p>
          </div>
        </div>
      </header>

      {loading ? <p className="empty-state"><Loader2 size={16} className="spin" aria-hidden="true" /> Loading report…</p> : null}
      {error ? <p className="submission-error">{error}</p> : null}

      {r ? (
        <>
          <div className={`recommendation-banner ${recommendationClass(report?.recommendation ?? null)}`}>
            <ScoreRing score={report?.score_total ?? 0} max={100} />
            <div className="rec-body">
              <p className="rec-label">Recommendation</p>
              <p className="rec-value">{recommendationLabel(report?.recommendation ?? null)}</p>
              <p className="rec-label" style={{ marginTop: 4 }}>
                {r.metadata.assessment.version}
              </p>
              {(r.integrity_score?.label ?? r.ai_integrity_risk.label) !== "low" ? (
                <span className={`status-pill ${riskClass(r.integrity_score?.label ?? r.ai_integrity_risk.label)}`} style={{ marginTop: 8, display: "inline-block" }}>
                  ⚠ Integrity risk: {r.integrity_score?.label ?? r.ai_integrity_risk.label}
                </span>
              ) : null}
            </div>
          </div>

          <IntegrityBanner integrityScore={r.integrity_score} aiRisk={r.ai_integrity_risk} />

          <section className="employer-section" id="section-public-tests">
            <SectionTitle title="Public tests" subtitle="Visible to the candidate during the attempt" />
            <ChartBar
              label="Passed"
              value={r.public_test_results.last_run_summary.passed}
              max={r.public_test_results.last_run_summary.collected || 1}
            />
            <p className="report-copy report-muted" style={{ marginTop: 8 }}>
              {r.public_test_results.run_count} test run(s) during the attempt.
            </p>
            {r.public_test_results.initially_failing_tests.length > 0 ? (
              <Disclosure label="Initially failing tests">
                <ul className="report-list">
                  {r.public_test_results.initially_failing_tests.map((t) => (<li key={t}>{t}</li>))}
                </ul>
              </Disclosure>
            ) : null}
          </section>

          <section className="employer-section" id="section-hidden-tests">
            <SectionTitle title="Hidden tests" subtitle="Evaluator edge-case tests run at submission" />
            <ChartBar
              label="Passed"
              value={r.hidden_test_results.summary.passed}
              max={r.hidden_test_results.summary.collected || 1}
            />
            {r.hidden_test_results.seeded_issue_areas.length > 0 ? (
              <Disclosure label="Seeded issue areas">
                <ul className="report-list">
                  {r.hidden_test_results.seeded_issue_areas.map((t) => (<li key={t}>{t}</li>))}
                </ul>
              </Disclosure>
            ) : null}
            {r.hidden_test_results.summary.failure_names.length > 0 ? (
              <Disclosure label="Failing hidden tests">
                <ul className="report-list">
                  {r.hidden_test_results.summary.failure_names.map((t) => (<li key={t}>{t}</li>))}
                </ul>
              </Disclosure>
            ) : null}
          </section>

          {r.feature_design_implementation ? (
            <section className="employer-section" id="section-enhancements">
              <SectionTitle title="Enhancements" subtitle="Feature/design implementation" />
              <ChartBar
                label={r.feature_design_implementation.category}
                value={r.feature_design_implementation.points}
                max={r.feature_design_implementation.max_points}
              />
              <p className="report-copy" style={{ marginTop: 8 }}>{r.feature_design_implementation.evidence}</p>
            </section>
          ) : null}

          <section className="employer-section" id="section-candidate-tests">
            <SectionTitle title="Candidate tests" subtitle="Tests written by the candidate" />
            <p className="report-copy">
              {r.candidate_tests.added_test_files.length} test file(s) added
              {r.candidate_tests.modified_test_files.length > 0
                ? `, ${r.candidate_tests.modified_test_files.length} modified`
                : ""}
              {r.candidate_tests.functions_added !== undefined ? ` · ${r.candidate_tests.functions_added} functions added` : ""}
              {r.candidate_tests.functions_modified !== undefined ? ` · ${r.candidate_tests.functions_modified} modified` : ""}
            </p>
          </section>

          <section className="employer-section" id="section-ai-collaboration">
            <SectionTitle title="AI collaboration" subtitle="How the candidate used the AI assistant" />
            <div className="process-mini-metrics">
              <div className="process-mini-metric">
                <span>Messages</span>
                <strong>{r.ai_collaboration.message_count}</strong>
              </div>
              <div className="process-mini-metric">
                <span>Candidate prompts</span>
                <strong>{r.ai_collaboration.candidate_prompt_count}</strong>
              </div>
              <div className="process-mini-metric">
                <span>Policy redirects</span>
                <strong>{r.ai_collaboration.policy_redirect_count}</strong>
              </div>
              <div className="process-mini-metric">
                <span>Large pastes</span>
                <strong>{r.ai_collaboration.large_paste_events.large_paste_count}</strong>
              </div>
            </div>
            {r.ai_collaboration.flagged_prompts.length > 0 ? (
              <Disclosure label={`Flagged prompts (${r.ai_collaboration.flagged_prompts.length})`}>
                <ul className="report-list">
                  {r.ai_collaboration.flagged_prompts.map((p, i) => (
                    <li key={i}>
                      <strong>{p.policy_tags.join(", ")}</strong> — {p.message}
                      <span className="report-muted"> · {new Date(p.at).toLocaleString()}</span>
                    </li>
                  ))}
                </ul>
              </Disclosure>
            ) : null}
          </section>

          <ProctoringSignalsSection signals={r.proctoring_signals} startedAt={r.metadata.timing?.started_at} />

          <section className="employer-section">
            <SectionTitle title="Submission review" subtitle="Candidate's own words" />
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

          <section className="report-grid">
            <article className="employer-section">
              <SectionTitle title="Process evidence" subtitle="How actively the candidate iterated" />
              <div className="process-mini-metrics">
                <div className="process-mini-metric">
                  <span>Snapshots</span>
                  <strong>{r.process_evidence.snapshot_count}</strong>
                </div>
                <div className="process-mini-metric">
                  <span>Test runs</span>
                  <strong>{r.process_evidence.test_run_count}</strong>
                </div>
              </div>
              {r.process_evidence.test_runs?.length ? (
                <Disclosure label="Test run details">
                  <ul className="report-list">
                    {r.process_evidence.test_runs.map((run) => (
                      <li key={run.id}>
                        {run.type} — {run.status}
                        {run.timings && Object.keys(run.timings).length ? (
                          <span className="report-muted">
                            {" "}· {formatMs(run.timings.api_total_ms ?? run.timings.worker_total_ms)}
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
                  {r.timeline.map((event) => (
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

          {r.submitted_code?.files ? (
            <section className="employer-section">
              <SectionTitle title="Submitted code" subtitle={`${r.submitted_code.file_count} file(s) submitted`} />
              <FileViewer files={r.submitted_code.files} />
            </section>
          ) : null}
        </>
      ) : null}
    </main>
  );
}