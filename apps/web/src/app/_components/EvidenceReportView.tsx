"use client";

import type { ReactNode } from "react";
import { useState } from "react";

import type { EvidenceReportResponse } from "../employer/types";

// Shared evidence-report renderer used by BOTH the employer report page and the super-admin
// report page. Keep all report rendering here so the two views never drift — the pages own
// only their header/loading/actions, not the report body.

export function recommendationLabel(value: string | null): string {
  if (!value) return "No recommendation";
  return value.replaceAll("_", " ");
}

export function recommendationClass(value: string | null): string {
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

function TestResultBar({ label, passed, collected }: { label: string; passed: number; collected: number }) {
  return <ChartBar label={label} value={passed} max={collected || 1} />;
}

function ScoreRing({ score, max }: { score: number; max: number }) {
  const pct = Math.max(0, Math.min(1, score / max));
  const r = 38;
  const circ = 2 * Math.PI * r;
  const dash = pct * circ;
  const color = pct >= 0.7 ? "#10b981" : pct >= 0.4 ? "#f59e0b" : "#ef4444";
  return (
    <svg width="96" height="96" viewBox="0 0 96 96" aria-hidden="true">
      <circle cx="48" cy="48" r={r} fill="none" stroke="#243357" strokeWidth="10" />
      <circle
        cx="48" cy="48" r={r} fill="none" stroke={color} strokeWidth="10"
        strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
        transform="rotate(-90 48 48)"
      />
      <text x="48" y="44" textAnchor="middle" fontSize="22" fontWeight="700" fill="#eef2ff" fontFamily="var(--font-mono)">{score}</text>
      <text x="48" y="62" textAnchor="middle" fontSize="12" fill="#7c91b8" fontFamily="var(--font-mono)">/ {max}</text>
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

function formatTimingValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return `${value} min`;
  return String(value);
}

function skillLabel(skillId: string): string {
  return skillId.replaceAll("_", " ").replaceAll(".", " / ");
}

function uniqueSkills(skills: Array<string | undefined>): string[] {
  return Array.from(new Set(skills.filter((skill): skill is string => Boolean(skill))));
}

function SkillList({ label, skills }: { label: string; skills?: string[] }) {
  const visibleSkills = uniqueSkills(skills ?? []);
  if (!visibleSkills.length) return null;
  return (
    <div>
      <p className="report-label">{label}</p>
      <div className="mod-tags">
        {visibleSkills.slice(0, 12).map((skill) => (
          <span className="mod-tag" key={skill}>{skillLabel(skill)}</span>
        ))}
      </div>
    </div>
  );
}

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

function formatMs(value: number | undefined): string {
  if (value === undefined) return "—";
  if (value >= 1000) return `${(value / 1000).toFixed(1)}s`;
  return `${value}ms`;
}

export function EvidenceReportView({ report }: { report: EvidenceReportResponse }) {
  const r = report.report;
  if (!r) return null;
  const timing = r.metadata?.timing;
  const featureScore = r.feature_design_implementation
    ?? r.scores?.categories?.find((cat: { category: string }) => cat.category === "Feature/design implementation");

  return (
    <>
      {/* Recommendation banner — with AI risk badge if elevated */}
      <div className={`recommendation-banner ${recommendationClass(report.recommendation ?? null)}`}>
        <ScoreRing score={report.score_total ?? 0} max={100} />
        <div className="rec-body">
          <p className="rec-label">Recommendation</p>
          <p className="rec-value">{recommendationLabel(report.recommendation ?? null)}</p>
          <p className="rec-label" style={{ marginTop: 4 }}>
            {r.metadata.assessment.version}
            {timing?.timing_mode ? ` · ${timing.timing_mode}` : ""}
          </p>
          {(r.integrity_score?.label ?? r.ai_integrity_risk.label) !== "low" ? (
            <span className={`status-pill ${riskClass(r.integrity_score?.label ?? r.ai_integrity_risk.label)}`} style={{ marginTop: 8, display: "inline-block" }}>
              ⚠ Integrity risk: {r.integrity_score?.label ?? r.ai_integrity_risk.label}
            </span>
          ) : null}
        </div>
      </div>

      <IntegrityBanner integrityScore={r.integrity_score} aiRisk={r.ai_integrity_risk} />

      {/* Attempt metadata metrics — with tooltips */}
      <section className="metric-row">
        <div
          className="metric"
          data-tooltip="Timed = hard cutoff with auto-submit on expiry. Untimed = recommended duration shown, not enforced."
        >
          <span>Timing</span>
          <strong>{timing?.timing_mode ?? "untimed"}</strong>
        </div>
        <div
          className="metric"
          data-tooltip={timing?.timing_mode === "timed"
            ? "Allowed duration vs. time the candidate actually used before submitting."
            : "How long the candidate worked from first open to submission."}
        >
          {timing?.timing_mode === "timed" ? (
            <>
              <span>Duration / used</span>
              <strong>{formatTimingValue(timing?.duration_minutes)} / {formatTimingValue(timing?.time_used_minutes)}</strong>
            </>
          ) : (
            <>
              <span>Time used</span>
              <strong>{formatTimingValue(timing?.time_used_minutes)}</strong>
            </>
          )}
        </div>
        <div
          className="metric"
          data-tooltip="Manual = candidate clicked Submit themselves. Auto (expired) = submitted automatically when the time limit ran out."
        >
          <span>Submission</span>
          <strong>{timing?.submission_mode === "auto_expired" ? "Auto (expired)" : "Manual"}</strong>
        </div>
        <div
          className="metric"
          data-tooltip="Strict = hidden test counts visible only in this report. Guided = candidate saw aggregate pass/fail counts during the attempt, but not the test details."
        >
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

      {r.adaptive_context ? (
        <section className="employer-section">
          <SectionTitle
            title="Role-adaptive context"
            subtitle="How the JD/resume blueprint maps to the selected assessment"
          />
          <div className="report-grid">
            <article>
              <p className="report-label">Role</p>
              <p className="report-copy">
                {r.adaptive_context.role.title} · {r.adaptive_context.role.seniority} · {r.adaptive_context.role.role_family}
              </p>
            </article>
            <article>
              <p className="report-label">Selected assessment</p>
              <p className="report-copy">
                {r.adaptive_context.selected_assessment.assessment_level}
                {" · "}
                {r.adaptive_context.selected_assessment.duration_minutes} min
                {" · "}
                {r.adaptive_context.selected_assessment.evaluator_feedback_mode}
              </p>
            </article>
          </div>
          <div className="report-grid" style={{ marginTop: 12 }}>
            <SkillList label="Directly tested" skills={r.adaptive_context.coverage.directly_tested} />
            <SkillList label="Partially tested" skills={r.adaptive_context.coverage.partially_tested} />
            <SkillList
              label="Not directly tested"
              skills={uniqueSkills([
                ...(r.adaptive_context.skill_mapping.unsupported_required ?? []),
                ...(r.adaptive_context.skill_mapping.unsupported_claimed ?? []),
              ])}
            />
          </div>
          {r.adaptive_context.rationale?.length ? (
            <Disclosure label="Blueprint rationale">
              <ul className="report-list">
                {r.adaptive_context.rationale.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </Disclosure>
          ) : null}
          {r.adaptive_context.caveats?.length ? (
            <Disclosure label="Coverage caveats">
              <ul className="report-list">
                {r.adaptive_context.caveats.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </Disclosure>
          ) : null}
        </section>
      ) : null}

      {/* Follow-up questions — right after exec summary */}
      {r.follow_up_questions?.length ? (
        <section className="employer-section followup-callout">
          <SectionTitle
            title="Suggested interview follow-ups"
            subtitle="Based on gaps, design decisions, and AI collaboration patterns in this submission"
          />
          <ol className="question-list">
            {r.follow_up_questions.map((q: string) => (
              <li key={q}>{q}</li>
            ))}
          </ol>
        </section>
      ) : null}

      {/* Score breakdown */}
      <section className="employer-section">
        <SectionTitle title="Score breakdown" />
        <div className="chart-list">
          {r.scores.categories.map((cat: { category: string; points: number; max_points: number }) => (
            <ChartBar
              key={cat.category}
              label={CATEGORY_LABELS[cat.category] ?? cat.category.replaceAll("_", " ")}
              value={cat.points}
              max={cat.max_points}
              anchor={SECTION_ANCHORS[cat.category]}
            />
          ))}
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
        <article id="section-enhancements" className="employer-section">
          <SectionTitle title="Enhancements" />
          <p className="report-copy">
            {featureScore
              ? `${featureScore.points}/${featureScore.max_points}: ${featureScore.evidence}`
              : "No feature/design score available."}
          </p>
        </article>

        <article className="employer-section">
          <SectionTitle
            title="FAVO interpretation"
            subtitle="Frame · Ask · Verify · Own — how the candidate structured their problem-solving process"
          />
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

      {/* Candidate tests + AI collaboration */}
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
            · integrity risk:{" "}
            <span className={r.ai_integrity_risk.label !== "low" ? `report-warn` : ""}>{r.ai_integrity_risk.label}</span>
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
        <SectionTitle title="Submission review" subtitle="Candidate's own words on what they changed and why" />
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

      {/* Process evidence — snapshot/iteration signal */}
      <section className="report-grid">
        <article className="employer-section">
          <SectionTitle
            title="Process evidence"
            subtitle="How actively the candidate iterated during the attempt"
          />
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

      <ProctoringSignalsSection signals={r.proctoring_signals} startedAt={r.metadata.timing?.started_at} />

      {/* Submitted code — at the bottom, it's reference material */}
      {r.submitted_code?.files ? (
        <section className="employer-section">
          <SectionTitle title="Submitted code" subtitle={`${r.submitted_code.file_count} file(s) submitted`} />
          <FileViewer files={r.submitted_code.files} />
        </section>
      ) : null}
    </>
  );
}
