"use client";

import { SignInButton, UserButton, useUser } from "@clerk/nextjs";
import { ClipboardCopy, FileText, LogIn, Plus, RefreshCw, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { createInvite, fetchAttempts } from "./api";
import type { EmployerAttemptSummary } from "./types";

const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
const isDev = process.env.NODE_ENV !== "production";

function formatDate(value: string | null): string {
  if (!value) return "Not submitted";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function recommendationLabel(value: string | null): string {
  if (!value) return "No report";
  return value.replaceAll("_", " ");
}

function AuthPanel({ onLocalLogin }: { onLocalLogin: () => void }) {
  return (
    <main className="employer-page">
      <section className="employer-auth">
        <div>
          <h1>SignalLoop Employer Portal</h1>
          <p>Review candidate attempts, create invites, and inspect generated evidence reports.</p>
        </div>
        <div className="auth-status">
          <ShieldCheck size={18} aria-hidden="true" />
          <span>{clerkConfigured ? "Clerk employer login is configured" : "Local dev login active until Clerk keys are configured"}</span>
        </div>
        {clerkConfigured ? (
          <SignInButton mode="modal">
            <button className="command-button primary">
              <LogIn size={18} aria-hidden="true" />
              Sign in with Clerk
            </button>
          </SignInButton>
        ) : null}
        {(!clerkConfigured || isDev) ? (
          <button className="command-button primary" onClick={onLocalLogin}>
            <LogIn size={18} aria-hidden="true" />
            Use local employer login
          </button>
        ) : null}
      </section>
    </main>
  );
}

function EmployerDashboard({ onLocalSignOut }: { onLocalSignOut?: () => void }) {
  const [attempts, setAttempts] = useState<EmployerAttemptSummary[]>([]);
  const [candidateEmail, setCandidateEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdInviteUrl, setCreatedInviteUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

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
      setAttempts(await fetchAttempts());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Attempt list failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void refreshAttempts();
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [refreshAttempts]);

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
      const updatedAttempts = await createInvite(candidateEmail.trim());
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
        {clerkConfigured ? <UserButton /> : null}
        {onLocalSignOut ? (
          <button className="command-button secondary" onClick={onLocalSignOut}>
            Sign out
          </button>
        ) : null}
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
            value={candidateEmail}
            onChange={(event) => setCandidateEmail(event.target.value)}
            placeholder="candidate@example.com"
          />
          <button className="command-button primary" disabled={creating} type="submit">
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
            <span>Submitted</span>
            <span>Report</span>
            <span>Action</span>
          </div>
          {attempts.map((attempt) => (
            <div className="attempt-row" key={attempt.attempt_id}>
              <span>{attempt.candidate_email ?? "No email"}</span>
              <span className={`status-pill ${attempt.status === "submitted" ? "ready" : "warn"}`}>
                {attempt.status}
              </span>
              <span>{formatDate(attempt.submitted_at)}</span>
              <span>{attempt.score_total ?? "-"} · {recommendationLabel(attempt.recommendation)}</span>
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

function ClerkEmployerPortal() {
  const { isLoaded, isSignedIn } = useUser();

  if (!isLoaded) {
    return (
      <main className="employer-page">
        <p className="empty-state">Loading employer session.</p>
      </main>
    );
  }

  if (!isSignedIn) {
    return <AuthPanel onLocalLogin={() => undefined} />;
  }

  return <EmployerDashboard />;
}

function DevPortal({
  localSessionActive,
  startDevSession,
  endDevSession,
}: {
  localSessionActive: boolean;
  startDevSession: () => void;
  endDevSession: () => void;
}) {
  const { isLoaded, isSignedIn } = useUser();

  if (!isLoaded) {
    return (
      <main className="employer-page">
        <p className="empty-state">Loading employer session.</p>
      </main>
    );
  }

  if (isSignedIn || localSessionActive) {
    return <EmployerDashboard onLocalSignOut={!isSignedIn ? endDevSession : undefined} />;
  }

  return <AuthPanel onLocalLogin={startDevSession} />;
}

export default function EmployerPortal() {
  const [localSessionActive, setLocalSessionActive] = useState(() => {
    if (typeof window === "undefined" || (clerkConfigured && !isDev)) {
      return false;
    }
    return localStorage.getItem("signalloop:employerSession") === "active";
  });

  function startDevSession() {
    localStorage.setItem("signalloop:employerSession", "active");
    setLocalSessionActive(true);
  }

  function endDevSession() {
    localStorage.removeItem("signalloop:employerSession");
    setLocalSessionActive(false);
  }

  if (clerkConfigured && !isDev) {
    return <ClerkEmployerPortal />;
  }

  if (clerkConfigured && isDev) {
    return <DevPortal localSessionActive={localSessionActive} startDevSession={startDevSession} endDevSession={endDevSession} />;
  }

  if (!localSessionActive) {
    return <AuthPanel onLocalLogin={startDevSession} />;
  }

  return <EmployerDashboard onLocalSignOut={endDevSession} />;
}
