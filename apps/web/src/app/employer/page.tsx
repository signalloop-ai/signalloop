"use client";

import { SignInButton, UserButton, useAuth, useUser } from "@clerk/nextjs";
import { ChevronDown, ClipboardCopy, FileText, HelpCircle, Info, Loader2, LogIn, Plus, ShieldCheck, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { createInvite, fetchAttempts, type AuthTokenProvider, type InviteConfiguration } from "./api";
import { fetchEmployerMe } from "../admin/api";
import type { EmployerAttemptSummary } from "./types";

// ── Static assessment pack details sourced from evaluator rubrics ──────────────

const ASSESSMENT_INFO = {
  standard: {
    title: "Standard FastAPI v2",
    description:
      "Candidates debug, harden, and extend an AI-generated task management API. The assessment tests how they reason about correctness, not just whether tests pass.",
    recommendedMinutes: 90,
    publicTests: [
      "Duplicate email → 409 (with case and whitespace normalization)",
      "Blank title → 422 (strip before validate)",
      "Non-owner task access → 403",
    ],
    hiddenTests: [
      "Email normalization: case-insensitive + whitespace-trimmed deduplication",
      "Priority normalization and validation (strip/upper, enum check, default)",
      "Full status transition chain: TODO → IN_PROGRESS → DONE enforced",
      "Unknown actor → 404, not 403 (existence leakage)",
    ],
    enhancements: [
      {
        name: "Task due date",
        detail: "Optional field; reject invalid formats and dates that don't make sense. Validation rules are left open — correctness is evaluated.",
      },
      {
        name: "Task listing",
        detail: "GET /tasks?owner_id=… returns a list. Ordering and empty-result behavior are left open and evaluated.",
      },
    ],
    scoring: [
      { category: "Public issue resolution", points: 15 },
      { category: "Hidden issue generalization", points: 20 },
      { category: "Enhancements", points: 20 },
      { category: "Candidate-written tests", points: 15 },
      { category: "AI collaboration", points: 15 },
      { category: "Regression", points: 15 },
    ],
  },
  advanced: {
    title: "Advanced FastAPI v1",
    description:
      "Candidates fix complex authorization, partial update, and role bugs in a multi-team service, then implement two non-trivial features. Requires reasoning about consistency, not just fixing isolated failures.",
    recommendedMinutes: 120,
    publicTests: [
      "Partial update overwrites omitted fields",
      "Team lead access is global instead of team-scoped",
      "Archived tasks visible in team list",
      "Comment endpoint has no access check",
    ],
    hiddenTests: [
      "Partial update authorization: non-owner, non-assignee, non-lead can PATCH",
      "Role validation: 'admin' accepted but should be 422",
      "Status transition: TODO → DONE direct transition should be blocked",
    ],
    enhancements: [
      {
        name: "Task dependencies",
        detail: "Blocking relationship with cycle detection (DFS/BFS), enforced on IN_PROGRESS transition. Endpoint shape is left open.",
      },
      {
        name: "Team activity feed",
        detail: "GET /teams/{id}/activity — team-scoped, members only, evaluated on pagination, ordering, and archived task handling.",
      },
    ],
    scoring: [
      { category: "Public issue resolution", points: 15 },
      { category: "Hidden issue generalization", points: 15 },
      { category: "Enhancements", points: 25 },
      { category: "Candidate-written tests", points: 15 },
      { category: "AI collaboration", points: 15 },
      { category: "Regression", points: 15 },
    ],
  },
} as const;

// ── Helpers ────────────────────────────────────────────────────────────────────

function recommendationLabel(value: string | null): string {
  if (!value) return "No report";
  return value.replaceAll("_", " ");
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 2) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="score-badge none">—</span>;
  const cls = score >= 80 ? "ready" : score >= 60 ? "warn" : "error";
  return <span className={`status-pill ${cls}`}>{score}/100</span>;
}

const Logo = () => (
  <svg className="topbar-logo" width="30" height="30" viewBox="0 0 30 30" fill="none" aria-label="SignalLoop">
    <rect width="30" height="30" rx="7" fill="#0f766e" />
    <path d="M15 6C19.97 6 24 10.03 24 15C24 19.97 19.97 24 15 24C10.5 24 6.8 20.7 6.1 16.4" stroke="white" strokeWidth="2.3" strokeLinecap="round" />
    <path d="M4.5 14.5L6.2 17.2L9 15.5" stroke="white" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="15" cy="6" r="2" fill="#5eead4" />
  </svg>
);

// ── Auth screen ────────────────────────────────────────────────────────────────

function AuthPanel() {
  return (
    <main className="employer-page">
      <section className="employer-auth">
        <div className="employer-brand">
          <Logo />
          <div>
            <h1>SignalLoop</h1>
            <p>Employer Portal</p>
          </div>
        </div>
        <div className="auth-status">
          <ShieldCheck size={18} aria-hidden="true" />
          <span>Sign in with your employer account to continue.</span>
        </div>
        <SignInButton mode="modal">
          <button className="command-button primary">
            <LogIn size={18} aria-hidden="true" />
            Sign in
          </button>
        </SignInButton>
      </section>
    </main>
  );
}

// ── Assessment detail modal ────────────────────────────────────────────────────

function AssessmentDetailModal({
  level,
  onClose,
}: {
  level: "standard" | "advanced";
  onClose: () => void;
}) {
  const info = ASSESSMENT_INFO[level];
  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="confirm-modal assessment-detail-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="assessment-detail-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="assessment-modal-header">
          <h2 id="assessment-detail-title">{info.title}</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <p className="assessment-modal-desc">{info.description}</p>
        <p className="assessment-modal-meta">Recommended time: {info.recommendedMinutes} min</p>

        <div className="assessment-section">
          <div className="assessment-section-header">
            <span className="assessment-count-badge">{info.publicTests.length}</span>
            Public tests
          </div>
          <p className="assessment-section-note">Visible to candidates during the attempt. All should pass before submitting.</p>
          <ul className="assessment-list">
            {info.publicTests.map((t) => <li key={t}>{t}</li>)}
          </ul>
        </div>

        <div className="assessment-section">
          <div className="assessment-section-header">
            <span className="assessment-count-badge hidden">{info.hiddenTests.length}</span>
            Hidden edge cases
          </div>
          <p className="assessment-section-note">Run at submission. Candidates know they exist but cannot see the tests.</p>
          <ul className="assessment-list">
            {info.hiddenTests.map((t) => <li key={t}>{t}</li>)}
          </ul>
        </div>

        <div className="assessment-section">
          <div className="assessment-section-header">
            <span className="assessment-count-badge enhancements">{info.enhancements.length}</span>
            Enhancements
          </div>
          <p className="assessment-section-note">Features candidates must design and implement. Evaluated on edge cases, not just the happy path.</p>
          <ul className="assessment-list">
            {info.enhancements.map((e) => (
              <li key={e.name}>
                <strong>{e.name}</strong> — {e.detail}
              </li>
            ))}
          </ul>
        </div>

        <div className="assessment-section">
          <div className="assessment-section-header">Scoring weights</div>
          <div className="assessment-scoring">
            {info.scoring.map((row) => (
              <div className="assessment-scoring-row" key={row.category}>
                <span>{row.category}</span>
                <span>{row.points} pts</span>
              </div>
            ))}
            <div className="assessment-scoring-row total">
              <span>Total</span>
              <span>100 pts</span>
            </div>
          </div>
        </div>

        <div className="modal-actions">
          <button className="command-button secondary" onClick={onClose}>Close</button>
        </div>
      </section>
    </div>
  );
}

// ── How it works ──────────────────────────────────────────────────────────────

function HowItWorks() {
  const [open, setOpen] = useState(false);
  return (
    <div className="how-it-works">
      <button
        className="how-it-works-toggle"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="how-it-works-label">
          <HelpCircle size={16} aria-hidden="true" />
          <span>How does this work?</span>
        </span>
        <ChevronDown size={16} className={`how-it-works-chevron${open ? " open" : ""}`} aria-hidden="true" />
      </button>

      <div className={`how-it-works-body${open ? " open" : ""}`} aria-hidden={!open}>
        <div className="how-it-works-inner">
          <div className="how-it-works-steps">
            <div className="hiw-step">
              <span className="hiw-step-num">1</span>
              <h3>Create an invite</h3>
              <p>Enter the candidate&apos;s email and pick the assessment settings:</p>
              <ul>
                <li><strong>Assessment</strong> — Standard (90 min) or Advanced (120 min)</li>
                <li><strong>Timing</strong> — Untimed (recommended) or hard cutoff with auto-submit</li>
                <li><strong>Evaluator feedback</strong> — Strict (results visible to you only) or Guided (candidate sees aggregate pass/fail counts)</li>
              </ul>
              <p>Copy the generated invite link and share it directly with the candidate.</p>
            </div>

            <div className="hiw-step">
              <span className="hiw-step-num">2</span>
              <h3>Candidate completes the assessment</h3>
              <p>The candidate opens the link in their browser and works in a proctored workspace:</p>
              <ul>
                <li>Reads the task brief and debugs a real API codebase</li>
                <li>Runs public tests and implements enhancements</li>
                <li>Collaborates with an AI assistant — their usage is logged</li>
                <li>Submits when done (or is auto-submitted if timed)</li>
              </ul>
              <p>Their status updates live in the table below: Invited → In progress → Submitted.</p>
            </div>

            <div className="hiw-step">
              <span className="hiw-step-num">3</span>
              <h3>Review the evidence report</h3>
              <p>Once submitted, click <strong>Generate</strong> next to their attempt. The report includes:</p>
              <ul>
                <li>Overall score and a hire / no-hire recommendation</li>
                <li>Hidden test results they couldn&apos;t see during the attempt</li>
                <li>AI collaboration log — what they asked and how they used responses</li>
                <li>Proctoring signals — fullscreen exits, focus loss, webcam snapshots</li>
                <li>Code diff and candidate-written test quality</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

function EmployerDashboard({ getAuthToken, isClerkLoaded }: { getAuthToken: AuthTokenProvider; isClerkLoaded: boolean }) {
  const [attempts, setAttempts] = useState<EmployerAttemptSummary[]>([]);
  const [candidateEmail, setCandidateEmail] = useState("");
  const [assessmentLevel, setAssessmentLevel] = useState<InviteConfiguration["assessmentLevel"]>("standard");
  const [timingMode, setTimingMode] = useState<InviteConfiguration["timingMode"]>("untimed");
  const [evaluatorFeedbackMode, setEvaluatorFeedbackMode] = useState<InviteConfiguration["evaluatorFeedbackMode"]>("strict");
  const [durationMinutes, setDurationMinutes] = useState(90);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdInviteUrl, setCreatedInviteUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [showAssessmentDetail, setShowAssessmentDetail] = useState(false);

  const emailValid = useMemo(() => {
    const trimmed = candidateEmail.trim();
    return trimmed.length > 0 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed);
  }, [candidateEmail]);

  const submittedCount = useMemo(
    () => attempts.filter((attempt) => attempt.status === "submitted").length,
    [attempts],
  );
  const reportCount = useMemo(
    () => attempts.filter((attempt) => attempt.report_id !== null).length,
    [attempts],
  );

  const refreshAttempts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setAttempts(await fetchAttempts(getAuthToken));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Attempt list failed");
    } finally {
      setLoading(false);
    }
  }, [getAuthToken]);

  useEffect(() => {
    if (!isClerkLoaded) return;
    void refreshAttempts();
    const interval = window.setInterval(() => void refreshAttempts(), 30_000);
    return () => window.clearInterval(interval);
  }, [refreshAttempts, isClerkLoaded]);

  function copyInviteUrl() {
    if (!createdInviteUrl) return;
    void navigator.clipboard.writeText(createdInviteUrl);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  async function submitInvite(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const updatedAttempts = await createInvite(
        candidateEmail.trim(),
        { assessmentLevel, timingMode, evaluatorFeedbackMode, durationMinutes },
        getAuthToken,
      );
      setAttempts(updatedAttempts);
      setCreatedInviteUrl(updatedAttempts[0]?.invite_url ?? null);
      setCandidateEmail("");
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Invite creation failed");
    } finally {
      setCreating(false);
    }
  }

  return (
    <main className="employer-page">
      <header className="employer-header">
        <div className="employer-brand">
          <Logo />
          <div>
            <h1>SignalLoop</h1>
            <p>Manage candidate assessments, track progress, and review AI-assisted evidence reports.</p>
          </div>
        </div>
        <UserButton />
      </header>

      <section className="metric-row">
        <div className="metric">
          <span>Total invites</span>
          <strong>{attempts.length}</strong>
        </div>
        <div className="metric">
          <span>Submitted</span>
          <strong>{submittedCount}</strong>
        </div>
        <div className="metric">
          <span>Reports ready</span>
          <strong>{reportCount}</strong>
        </div>
      </section>

      <HowItWorks />

      <section className="employer-section">
        <div className="section-title">
          <h2>Create invite</h2>
        </div>
        <form className="invite-form" onSubmit={submitInvite}>
          {/* Row 1: email + submit button side by side */}
          <label htmlFor="candidate-email">Candidate email</label>
          <input
            id="candidate-email"
            type="email"
            required
            value={candidateEmail}
            onChange={(event) => setCandidateEmail(event.target.value)}
            placeholder="candidate@example.com"
            aria-describedby={candidateEmail && !emailValid ? "email-error" : undefined}
          />
          <button className="command-button primary" disabled={creating || !emailValid} type="submit">
            {creating
              ? <><Loader2 size={15} className="spin" aria-hidden="true" /> Creating…</>
              : <><Plus size={17} aria-hidden="true" /> Create invite</>
            }
          </button>
          {candidateEmail && !emailValid ? (
            <span id="email-error" className="submission-error" style={{ gridColumn: "1 / -1", marginTop: 0 }}>
              Enter a valid email address
            </span>
          ) : null}

          {/* Invite URL appears immediately after the email row */}
          {createdInviteUrl ? (
            <div className="invite-result" style={{ gridColumn: "1 / -1" }}>
              <input
                className="invite-url-input"
                readOnly
                value={createdInviteUrl}
                onFocus={(e) => e.currentTarget.select()}
                aria-label="Invite URL"
              />
              <button type="button" className="command-button secondary" onClick={copyInviteUrl}>
                <ClipboardCopy size={16} aria-hidden="true" />
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
          ) : null}

          {/* Row 2: assessment select + Details button side by side */}
          <label htmlFor="assessment-level">Assessment</label>
          <select
            id="assessment-level"
            value={assessmentLevel}
            onChange={(event) => {
              const nextLevel = event.target.value as InviteConfiguration["assessmentLevel"];
              setAssessmentLevel(nextLevel);
              setDurationMinutes(nextLevel === "advanced" ? 120 : 90);
            }}
          >
            <option value="standard">Standard FastAPI v2 — 3 bugs · 4 hidden · 2 enhancements · 90 min</option>
            <option value="advanced">Advanced FastAPI v1 — 4 bugs · 3 hidden · 2 enhancements · 120 min</option>
          </select>
          <button
            type="button"
            className="form-action-btn"
            onClick={() => setShowAssessmentDetail(true)}
          >
            <Info size={14} aria-hidden="true" />
            Details
          </button>

          {/* Remaining selects span both columns */}
          <label htmlFor="timing-mode">Timing</label>
          <select
            id="timing-mode"
            style={{ gridColumn: "1 / -1" }}
            value={timingMode}
            onChange={(event) => setTimingMode(event.target.value as InviteConfiguration["timingMode"])}
          >
            <option value="untimed">Untimed — recommended time shown, not enforced</option>
            <option value="timed">Timed — hard cutoff, auto-submit on expiry</option>
          </select>
          {timingMode === "timed" ? (
            <>
              <label htmlFor="duration-minutes">Duration</label>
              <select
                id="duration-minutes"
                style={{ gridColumn: "1 / -1" }}
                value={durationMinutes}
                onChange={(event) => setDurationMinutes(Number(event.target.value))}
              >
                <option value={60}>60 minutes</option>
                <option value={90}>90 minutes</option>
                <option value={120}>120 minutes</option>
                <option value={150}>150 minutes</option>
              </select>
            </>
          ) : null}

          <label htmlFor="evaluator-feedback-mode">Evaluator feedback</label>
          <select
            id="evaluator-feedback-mode"
            style={{ gridColumn: "1 / -1" }}
            value={evaluatorFeedbackMode}
            onChange={(event) => setEvaluatorFeedbackMode(event.target.value as InviteConfiguration["evaluatorFeedbackMode"])}
          >
            <option value="strict">Strict — hidden results in employer report only</option>
            <option value="guided">Guided — candidate sees aggregate pass/fail counts (no test details)</option>
          </select>
        </form>

        {error ? <p className="submission-error">{error}</p> : null}
      </section>

      <section className="employer-section">
        <div className="section-title">
          <h2>Candidate attempts</h2>
          {loading ? <span className="autosave-chip">Refreshing…</span> : null}
        </div>
        <div className="attempt-table">
          <div className="attempt-row table-head">
            <span>Candidate</span>
            <span>Status</span>
            <span>Configuration</span>
            <span>Score</span>
            <span>Action</span>
          </div>
          {attempts.map((attempt) => (
            <div className="attempt-row" key={attempt.attempt_id}>
              <div className="attempt-email-meta">
                <span>{attempt.candidate_email ?? "No email"}</span>
                <span className="attempt-sent-at">{timeAgo(attempt.created_at)}</span>
              </div>
              <span>
                <span className={`status-pill ${attempt.status === "submitted" ? "ready" : attempt.status === "expired" ? "error" : "warn"}`}>
                  {attempt.status === "created" ? "Invited"
                    : attempt.status === "opened" || attempt.status === "in_progress" || attempt.status === "started" ? "In progress"
                    : attempt.status === "submitted" ? "Submitted"
                    : attempt.status === "expired" ? "Expired"
                    : attempt.status}
                </span>
                <span className="attempt-level-tag">{attempt.assessment_level}</span>
              </span>
              <span className="attempt-config">
                {attempt.timing_mode === "timed" ? `Timed ${attempt.duration_minutes} min` : "Untimed"}
                {" · "}
                {attempt.evaluator_feedback_mode}
              </span>
              <span>
                {attempt.recommendation ? (
                  <span className="attempt-recommendation">{recommendationLabel(attempt.recommendation)}</span>
                ) : (
                  <ScoreBadge score={attempt.score_total} />
                )}
              </span>
              {attempt.status === "submitted" ? (
                <Link className="command-button secondary" href={`/employer/reports/${attempt.attempt_id}`}>
                  <FileText size={16} aria-hidden="true" />
                  {attempt.report_id ? "View report" : "Generate"}
                </Link>
              ) : (
                <span className="empty-state">Awaiting submission</span>
              )}
            </div>
          ))}
          {!attempts.length && !loading ? (
            <p className="empty-state">No candidates invited yet — create an invite above to get started.</p>
          ) : null}
        </div>
      </section>

      {showAssessmentDetail ? (
        <AssessmentDetailModal
          level={assessmentLevel}
          onClose={() => setShowAssessmentDetail(false)}
        />
      ) : null}
    </main>
  );
}

// ── Root ──────────────────────────────────────────────────────────────────────

export default function EmployerPortal() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();
  const [roleChecked, setRoleChecked] = useState(false);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    let cancelled = false;
    (async () => {
      try {
        const me = await fetchEmployerMe(getToken);
        if (!cancelled && me.role === "super_admin") {
          router.replace("/admin");
          return;
        }
      } catch {
        // If /employer/me fails, proceed to employer dashboard (auth error handled by API)
      }
      if (!cancelled) setRoleChecked(true);
    })();
    return () => { cancelled = true; };
  }, [isLoaded, isSignedIn, getToken, router]);

  if (!isLoaded) {
    return (
      <main className="employer-page">
        <p className="empty-state">Loading employer session.</p>
      </main>
    );
  }

  if (!isSignedIn) {
    return <AuthPanel />;
  }

  if (!roleChecked) {
    return (
      <main className="employer-page">
        <p className="empty-state">Loading employer session.</p>
      </main>
    );
  }

  return <EmployerDashboard getAuthToken={getToken} isClerkLoaded={isLoaded} />;
}
