"use client";

import { SignInButton, UserButton, useAuth, useUser } from "@clerk/nextjs";
import { ClipboardCopy, FileText, LogIn, Plus, RefreshCw, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { createInvite, fetchAttempts, type AuthTokenProvider, type InviteConfiguration } from "./api";
import type { EmployerAttemptSummary } from "./types";

function recommendationLabel(value: string | null): string {
  if (!value) return "No report";
  return value.replaceAll("_", " ");
}

function AuthPanel() {
  return (
    <main className="employer-page">
      <section className="employer-auth">
        <div>
          <h1>SignalLoop Employer Portal</h1>
          <p>Review candidate attempts, create invites, and inspect generated evidence reports.</p>
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
    const timeoutId = window.setTimeout(() => {
      void refreshAttempts();
    }, 0);
    return () => window.clearTimeout(timeoutId);
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
        <div>
          <h1>Employer Review</h1>
          <p>Minimal MVP portal for invites, attempts, and evidence reports.</p>
        </div>
        <button className="command-button secondary" disabled={loading} onClick={refreshAttempts}>
          <RefreshCw size={17} aria-hidden="true" />
          {loading ? "Refreshing" : "Refresh"}
        </button>
        <UserButton />
      </header>

      <section className="metric-row">
        <div className="metric">
          <span>Total attempts</span>
          <strong>{attempts.length}</strong>
        </div>
        <div className="metric">
          <span>Submitted</span>
          <strong>{submittedCount}</strong>
        </div>
        <div className="metric">
          <span>Reports</span>
          <strong>{reportCount}</strong>
        </div>
      </section>

      <section className="employer-section">
        <div className="section-title">
          <h2>Create invite</h2>
        </div>
        <form className="invite-form" onSubmit={submitInvite}>
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
          {candidateEmail && !emailValid ? (
            <span id="email-error" className="submission-error" style={{ marginTop: 0 }}>Enter a valid email address</span>
          ) : null}
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
            <option value="standard">Standard FastAPI v2</option>
            <option value="advanced">Advanced FastAPI v1</option>
          </select>
          <label htmlFor="timing-mode">Timing</label>
          <select
            id="timing-mode"
            value={timingMode}
            onChange={(event) => setTimingMode(event.target.value as InviteConfiguration["timingMode"])}
          >
            <option value="untimed">Untimed, recommended time only</option>
            <option value="timed">Timed</option>
          </select>
          {timingMode === "timed" ? (
            <>
              <label htmlFor="duration-minutes">Duration</label>
              <select
                id="duration-minutes"
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
            value={evaluatorFeedbackMode}
            onChange={(event) => setEvaluatorFeedbackMode(event.target.value as InviteConfiguration["evaluatorFeedbackMode"])}
          >
            <option value="strict">Strict: hidden counts in employer report only</option>
            <option value="guided">Guided: show aggregate evaluator progress</option>
          </select>
          <p className="submission-help">
            Guided mode shows candidates aggregate evaluator pass/fail counts only. Details stay hidden.
          </p>
          <button className="command-button primary" disabled={creating || !emailValid} type="submit">
            <Plus size={17} aria-hidden="true" />
            {creating ? "Creating" : "Create invite"}
          </button>
        </form>
        {createdInviteUrl ? (
          <div className="invite-result">
            <button className="command-button secondary" onClick={copyInviteUrl}>
              <ClipboardCopy size={16} aria-hidden="true" />
              {copied ? "Copied!" : "Copy"}
            </button>
            <span>{createdInviteUrl}</span>
          </div>
        ) : null}
        {error ? <p className="submission-error">{error}</p> : null}
      </section>

      <section className="employer-section">
        <div className="section-title">
          <h2>Candidate attempts</h2>
        </div>
        <div className="attempt-table">
          <div className="attempt-row table-head">
            <span>Candidate</span>
            <span>Status</span>
            <span>Timing</span>
            <span>Report</span>
            <span>Action</span>
          </div>
          {attempts.map((attempt) => (
            <div className="attempt-row" key={attempt.attempt_id}>
              <span>{attempt.candidate_email ?? "No email"}</span>
              <span className={`status-pill ${attempt.status === "submitted" ? "ready" : "warn"}`}>
                {attempt.assessment_level} · {attempt.status}
              </span>
              <span>
                {attempt.timing_mode === "timed" ? `Timed ${attempt.duration_minutes}m` : "Untimed"}
                {" · "}
                {attempt.evaluator_feedback_mode}
              </span>
              <span>
                {attempt.score_total != null ? `Score: ${attempt.score_total} / 100` : "—"}
                {attempt.recommendation ? ` · ${recommendationLabel(attempt.recommendation)}` : ""}
              </span>
              {attempt.status === "submitted" ? (
                <Link className="command-button secondary" href={`/employer/reports/${attempt.attempt_id}`}>
                  <FileText size={16} aria-hidden="true" />
                  {attempt.report_id ? "View" : "Generate"}
                </Link>
              ) : (
                <span className="empty-state">Awaiting submission</span>
              )}
            </div>
          ))}
          {!attempts.length && !loading ? <p className="empty-state">No attempts yet.</p> : null}
        </div>
      </section>
    </main>
  );
}

export default function EmployerPortal() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();

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

  return <EmployerDashboard getAuthToken={getToken} isClerkLoaded={isLoaded} />;
}
