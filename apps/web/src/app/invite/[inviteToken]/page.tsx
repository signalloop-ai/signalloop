"use client";

import Editor from "@monaco-editor/react";
import {
  CheckCircle2,
  ClipboardCheck,
  FileCode2,
  FolderTree,
  MessageSquare,
  Play,
  Send,
  ShieldAlert,
} from "lucide-react";
import { useParams } from "next/navigation";
import type { CSSProperties, PointerEvent } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type AssessmentMetadata = {
  slug: string;
  title: string;
  version: string;
  seeded_issue_count: number;
};

type CandidateAttempt = {
  attempt_id: number;
  status: string;
  candidate_email: string | null;
  assessment: AssessmentMetadata;
  timing_mode: string;
  duration_minutes: number;
  started_at: string | null;
  expires_at: string | null;
  submitted_at: string | null;
  submission_mode: string | null;
  files: Record<string, string>;
};

type TestResult = {
  status: "passed" | "failed" | "error" | "timeout";
  exit_code: number | null;
  stdout: string;
  stderr: string;
  duration_ms: number;
};

type ChatMessage = {
  role: "candidate" | "assistant";
  content: string;
  allowed?: boolean;
  tags?: string[];
};

type AIMessageResponse = {
  message: string;
  allowed: boolean;
  policy_tags: string[];
};

type FinalSubmissionResponse = {
  attempt_id: number;
  status: string;
  submission_id: number;
  snapshot_id: number;
  hidden_test_run_id: number | null;
  hidden_test_status: string;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

function languageForPath(path: string): string {
  if (path.endsWith(".py")) return "python";
  if (path.endsWith(".md")) return "markdown";
  if (path.endsWith(".toml")) return "toml";
  if (path.endsWith(".txt")) return "plaintext";
  return "plaintext";
}

function resultText(result: TestResult | null, error: string | null): string {
  if (error) return error;
  if (!result) return "Public test output will appear here.";

  const header = [
    `status: ${result.status}`,
    `exit_code: ${result.exit_code ?? "none"}`,
    `duration_ms: ${result.duration_ms}`,
  ].join("\n");

  return [header, result.stdout, result.stderr].filter(Boolean).join("\n\n");
}

function statusClass(status: string): string {
  if (status === "passed" || status === "submitted") return "ready";
  if (status === "failed" || status === "error" || status === "timeout") return "error";
  return "warn";
}

function formatCountdown(msRemaining: number): string {
  const clamped = Math.max(0, msRemaining);
  const totalSeconds = Math.ceil(clamped / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

export default function CandidateWorkspace() {
  const routeParams = useParams<{ inviteToken: string | string[] }>();
  const inviteTokenParam = routeParams.inviteToken;
  const inviteToken = Array.isArray(inviteTokenParam) ? inviteTokenParam[0] : inviteTokenParam;
  const [accepted, setAccepted] = useState(false);
  const [attempt, setAttempt] = useState<CandidateAttempt | null>(null);
  const [files, setFiles] = useState<Record<string, string>>({});
  const [activePath, setActivePath] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [testError, setTestError] = useState<string | null>(null);
  const [initialFiles, setInitialFiles] = useState<Record<string, string>>({});
  const [submissionReview, setSubmissionReview] = useState({
    changed: "",
    tradeoffs: "",
    verification: "",
    nextSteps: "",
    notes: "",
  });
  const [confirmingSubmit, setConfirmingSubmit] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submissionResult, setSubmissionResult] = useState<FinalSubmissionResponse | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "I can help with one candidate-identified issue or one failing public behavior at a time.",
      allowed: true,
      tags: ["guardrails"],
    },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [filePanelWidth, setFilePanelWidth] = useState(240);
  const [assistantPanelWidth, setAssistantPanelWidth] = useState(320);
  const [bottomPanelHeight, setBottomPanelHeight] = useState(240);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const submissionReviewRef = useRef<HTMLTextAreaElement | null>(null);
  const submissionPanelRef = useRef<HTMLDivElement | null>(null);
  const chatMessagesRef = useRef<HTMLDivElement | null>(null);
  const autoSnapshotTimeoutRef = useRef<number | null>(null);
  const autoSubmittedRef = useRef(false);

  useEffect(() => {
    async function loadInvite() {
      setLoading(true);
      setLoadError(null);
      try {
        const response = await fetch(`${apiBaseUrl}/candidate/invites/${inviteToken}`);
        if (!response.ok) {
          throw new Error(`Invite load failed with HTTP ${response.status}`);
        }
        const body = (await response.json()) as CandidateAttempt;
        setAttempt(body);
        setFiles(body.files);
        setInitialFiles(body.files);
        setActivePath(Object.keys(body.files).sort()[0] ?? "");
        setSubmitted(body.status === "submitted");
        setAccepted(Boolean(body.started_at) || body.status === "submitted");
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Invite load failed");
      } finally {
        setLoading(false);
      }
    }

    loadInvite();
  }, [inviteToken]);

  useEffect(() => {
    const el = chatMessagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [chatMessages]);

  useEffect(() => {
    return () => {
      if (autoSnapshotTimeoutRef.current) window.clearTimeout(autoSnapshotTimeoutRef.current);
    };
  }, []);

  useEffect(() => {
    const intervalId = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(intervalId);
  }, []);

  const sortedFiles = useMemo(() => Object.keys(files).sort(), [files]);
  const activeContent = activePath ? files[activePath] ?? "" : "";
  const reviewRequiredAnswers = [
    submissionReview.changed,
    submissionReview.tradeoffs,
    submissionReview.verification,
    submissionReview.nextSteps,
  ];
  const reviewAnsweredCount = reviewRequiredAnswers.filter((value) => value.trim().length > 0).length;
  const candidateTestsAdded = useMemo(
    () => Object.keys(files).some((path) => path.startsWith("tests/") && files[path] !== initialFiles[path]),
    [files, initialFiles],
  );
  const publicTestsRun = testResult !== null || testError !== null;
  const canSubmit = !submitted && !submitting && !running;
  const expiresAtMs = attempt?.expires_at ? Date.parse(attempt.expires_at) : null;
  const msRemaining = expiresAtMs ? expiresAtMs - nowMs : null;
  const isTimed = attempt?.timing_mode === "timed" && expiresAtMs !== null;
  const isExpired = Boolean(isTimed && msRemaining !== null && msRemaining <= 0);
  const timerWarning =
    isTimed && msRemaining !== null && msRemaining <= 60_000
      ? "1 minute remaining"
      : isTimed && msRemaining !== null && msRemaining <= 5 * 60_000
        ? "5 minutes remaining"
        : isTimed && msRemaining !== null && msRemaining <= 10 * 60_000
          ? "10 minutes remaining"
          : null;

  function focusSubmission() {
    setBottomPanelHeight((current) => Math.max(current, 300));
    window.setTimeout(() => submissionReviewRef.current?.focus(), 0);
  }

  const publicRunMessage = running
    ? "Running public tests in an isolated AWS task. This usually takes 20-30 seconds; the result applies to the code snapshot from when you clicked Run Tests."
    : null;
  const submissionMessage = submitting
    ? "Submitting final code and running hidden evaluation in an isolated AWS task. This usually takes 20-30 seconds; keep this tab open until the result appears."
    : null;

  function startHorizontalResize(
    event: PointerEvent<HTMLDivElement>,
    panel: "files" | "assistant",
  ) {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = panel === "files" ? filePanelWidth : assistantPanelWidth;

    function onPointerMove(moveEvent: globalThis.PointerEvent) {
      const delta = moveEvent.clientX - startX;
      if (panel === "files") {
        setFilePanelWidth(Math.min(420, Math.max(180, startWidth + delta)));
      } else {
        setAssistantPanelWidth(Math.min(520, Math.max(260, startWidth - delta)));
      }
    }

    function onPointerUp() {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    }

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
  }

  function startVerticalResize(event: PointerEvent<HTMLDivElement>) {
    event.preventDefault();
    const startY = event.clientY;
    const startHeight = bottomPanelHeight;

    function onPointerMove(moveEvent: globalThis.PointerEvent) {
      const delta = startY - moveEvent.clientY;
      setBottomPanelHeight(Math.min(430, Math.max(190, startHeight + delta)));
    }

    function onPointerUp() {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    }

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
  }

  async function saveSnapshot(kind = "autosave") {
    if (submitted) return;
    try {
      const response = await fetch(`${apiBaseUrl}/candidate/invites/${inviteToken}/snapshots`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind, files }),
      });
      if (!response.ok) {
        throw new Error(`Snapshot failed with HTTP ${response.status}`);
      }
      setSaveStatus(kind === "autosave" ? "Auto-snapshot saved." : "Snapshot saved before test run.");
    } catch (error) {
      setSaveStatus(error instanceof Error ? error.message : "Snapshot failed.");
    }
  }

  async function runPublicTests() {
    if (submitted) return;
    setRunning(true);
    setTestError(null);
    setTestResult(null);
    try {
      const response = await fetch(`${apiBaseUrl}/candidate/invites/${inviteToken}/run-public-tests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ files, kind: "public_test_run" }),
      });
      if (!response.ok) {
        throw new Error(`Test run failed with HTTP ${response.status}`);
      }
      setTestResult((await response.json()) as TestResult);
    } catch (error) {
      setTestError(error instanceof Error ? error.message : "Public test run failed");
    } finally {
      setRunning(false);
    }
  }

  async function acceptRules() {
    try {
      const response = await fetch(`${apiBaseUrl}/candidate/invites/${inviteToken}/accept`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error(`Accept failed with HTTP ${response.status}`);
      }
      const body = (await response.json()) as CandidateAttempt;
      setAttempt(body);
      setFiles(body.files);
      setInitialFiles(body.files);
      setActivePath(Object.keys(body.files).sort()[0] ?? "");
      setSubmitted(body.status === "submitted");
      setAccepted(true);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Accept failed");
    }
  }

  const submitFinal = useCallback(async (submissionMode: "manual" | "auto_expired" = "manual") => {
    if (submissionMode === "manual" && !canSubmit) return;
    setSubmitting(true);
    setConfirmingSubmit(false);
    setSubmitError(null);
    const finalExplanation = [
      `What changed: ${submissionReview.changed.trim() || "Not answered."}`,
      `Tradeoffs/product decisions: ${submissionReview.tradeoffs.trim() || "Not answered."}`,
      `Verification: ${submissionReview.verification.trim() || "Not answered."}`,
      `Improve next: ${submissionReview.nextSteps.trim() || "Not answered."}`,
      submissionReview.notes.trim() ? `Additional notes: ${submissionReview.notes.trim()}` : "",
    ].filter(Boolean).join("\n\n");
    const decisionLog = submissionReview.tradeoffs.trim();
    try {
      const response = await fetch(`${apiBaseUrl}/candidate/invites/${inviteToken}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          files,
          final_explanation: finalExplanation,
          decision_log: decisionLog,
          submission_mode: submissionMode,
        }),
      });
      if (!response.ok) {
        let detail = `Submission failed (HTTP ${response.status})`;
        try {
          const err = await response.json();
          if (Array.isArray(err.errors) && err.errors[0]?.msg) {
            const e = err.errors[0];
            const field = Array.isArray(e.loc) ? e.loc.slice(1).join(".") : "";
            detail = field ? `${field}: ${e.msg}` : e.msg;
          } else if (typeof err.detail === "string") {
            detail = err.detail;
          }
        } catch {}
        throw new Error(detail);
      }
      const body = (await response.json()) as FinalSubmissionResponse;
      setSubmitted(true);
      setSubmissionResult(body);
      setAttempt((current) => (current ? {
        ...current,
        status: body.status,
        submitted_at: new Date().toISOString(),
        submission_mode: submissionMode,
      } : current));
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  }, [canSubmit, files, inviteToken, submissionReview]);

  useEffect(() => {
    if (!isExpired || submitted || submitting || autoSubmittedRef.current) return;
    autoSubmittedRef.current = true;
    void submitFinal("auto_expired");
  }, [isExpired, submitted, submitting, submitFinal]);

  async function sendChatMessage() {
    const message = chatInput.trim();
    if (!message) return;

    setChatInput("");
    setChatLoading(true);
    setChatMessages((current) => [...current, { role: "candidate", content: message }]);
    try {
      const response = await fetch(`${apiBaseUrl}/candidate/invites/${inviteToken}/ai/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          selected_context: activePath
            ? {
                path: activePath,
                content: files[activePath] ?? "",
              }
            : undefined,
        }),
      });
      if (!response.ok) {
        throw new Error(`Assistant returned HTTP ${response.status}`);
      }
      const body = (await response.json()) as AIMessageResponse;
      setChatMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: body.message,
          allowed: body.allowed,
          tags: body.policy_tags,
        },
      ]);
    } catch (error) {
      setChatMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: error instanceof Error ? error.message : "Assistant request failed",
          allowed: false,
          tags: ["request_error"],
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  if (loading) {
    return (
      <main className="onboarding">
        <section className="onboarding-panel">
          <h1>Loading assessment</h1>
          <p>Opening the invite and preparing candidate files.</p>
        </section>
      </main>
    );
  }

  if (loadError || !attempt) {
    return (
      <main className="onboarding">
        <section className="onboarding-panel">
          <ShieldAlert size={32} color="var(--danger)" aria-hidden="true" />
          <h1>Invite unavailable</h1>
          <p>{loadError ?? "The invite could not be loaded."}</p>
        </section>
      </main>
    );
  }

  if (!accepted) {
    return (
      <main className="onboarding">
        <section className="onboarding-panel">
          <div>
            <h1>{attempt.assessment.title}</h1>
            <p>
              You are joining an internal beta hardening exercise. Public tests are
              incomplete; your job is to reason about the code, make focused fixes,
              add tests for changed behavior, and explain your decisions.
            </p>
          </div>
          <ul>
            <li>Security and data isolation are more important than convenience.</li>
            <li>Do not change the public API shape unless you can justify it.</li>
            <li>Where requirements are ambiguous, choose a policy and apply it consistently.</li>
            <li>Use public test output as evidence, not as the only source of truth.</li>
          </ul>
          {attempt.timing_mode === "timed" ? (
            <p>
              This is a timed attempt. Your {attempt.duration_minutes}-minute timer starts when you accept.
            </p>
          ) : (
            <p>This attempt is untimed. Recommended completion time is {attempt.duration_minutes} minutes.</p>
          )}
          <button className="command-button primary" onClick={acceptRules}>
            <CheckCircle2 size={18} aria-hidden="true" />
            Accept rules
          </button>
        </section>
      </main>
    );
  }

  return (
    <main
      className="workspace-shell"
      style={
        {
          "--file-panel-width": `${filePanelWidth}px`,
          "--assistant-panel-width": `${assistantPanelWidth}px`,
          "--bottom-panel-height": `${bottomPanelHeight}px`,
        } as CSSProperties
      }
    >
      <header className="topbar">
        <div className="topbar-title">
          <h1>{attempt.assessment.title}</h1>
          <p>
            Attempt #{attempt.attempt_id} · {attempt.candidate_email ?? "candidate invite"} ·{" "}
            {attempt.assessment.version}
          </p>
        </div>
        <div className="topbar-actions">
          <span className={`status-pill ${statusClass(submitted ? "submitted" : attempt.status)}`}>
            {submitted ? "submitted" : attempt.status}
          </span>
          {isTimed && msRemaining !== null ? (
            <span className={`status-pill ${isExpired ? "error" : timerWarning ? "warn" : "ready"}`}>
              {isExpired ? "Expired" : `Time ${formatCountdown(msRemaining)}`}
            </span>
          ) : (
            <span className="status-pill ready">Recommended {attempt.duration_minutes}m</span>
          )}
          {timerWarning && !isExpired ? <span className="operation-status">{timerWarning}</span> : null}
          {submissionResult ? (
            <span className="submission-status">
              {submissionResult.hidden_test_status === "passed"
                ? "All hidden tests passed."
                : "Some hidden tests failed."}
            </span>
          ) : null}
          {publicRunMessage ? <span className="operation-status">{publicRunMessage}</span> : null}
          {submissionMessage ? <span className="operation-status">{submissionMessage}</span> : null}
          <button className="command-button primary" disabled={running || submitted} onClick={runPublicTests}>
            <Play size={17} aria-hidden="true" />
            {running ? "Running" : "Run Tests"}
          </button>
          <button className="command-button secondary" onClick={focusSubmission}>
            <ClipboardCheck size={17} aria-hidden="true" />
            Submission
          </button>
          <button className="command-button primary" disabled={!canSubmit} onClick={() => setConfirmingSubmit(true)}>
            <Send size={17} aria-hidden="true" />
            {submitting ? "Submitting" : "Submit"}
          </button>
        </div>
      </header>

      <section className="workspace-grid">
        <aside className="sidebar">
          <div className="panel-header">
            <h2>Files</h2>
            <p>Candidate-visible workspace files only.</p>
          </div>
          <div className="workflow-card">
            <h3>What to do</h3>
            <ol>
              <li>Inspect the FastAPI app and public tests.</li>
              <li>Fix focused issues and add tests where useful.</li>
              <li>Run public tests to gather evidence.</li>
              <li>Use AI for one issue or failing behavior at a time.</li>
              <li>Complete the submission review, then submit.</li>
            </ol>
            <p>Tests do not need to pass before submission. Review answers are supporting evidence; implementation and verification matter most.</p>
          </div>
          <div className="file-list">
            {sortedFiles.map((path) => (
              <button
                className={`file-row ${path === activePath ? "active" : ""}`}
                key={path}
                onClick={() => setActivePath(path)}
                title={path}
              >
                <FileCode2 size={16} aria-hidden="true" />
                <span>{path}</span>
              </button>
            ))}
          </div>
        </aside>
        <div
          className="resize-handle vertical"
          onPointerDown={(event) => startHorizontalResize(event, "files")}
          role="separator"
          aria-label="Resize file panel"
        />

        <section className="editor-zone">
          <div className="editor-tabs">
            <div className="active-file" title={activePath}>
              <FolderTree size={16} aria-hidden="true" />
              <span>{activePath || "No file selected"}</span>
            </div>
          </div>
          <div className="editor-wrapper">
            <Editor
              height="100%"
              language={languageForPath(activePath)}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                lineNumbersMinChars: 3,
                scrollBeyondLastLine: false,
                wordWrap: "on",
                automaticLayout: true,
                readOnly: submitted,
              }}
              theme="vs-dark"
              value={activeContent}
              onChange={(value) => {
                if (!activePath) return;
                setFiles((current) => ({ ...current, [activePath]: value ?? "" }));
                setSaveStatus("Unsaved changes.");
                if (autoSnapshotTimeoutRef.current) window.clearTimeout(autoSnapshotTimeoutRef.current);
                autoSnapshotTimeoutRef.current = window.setTimeout(() => {
                  void saveSnapshot("autosave");
                }, 60_000);
              }}
            />
          </div>
        </section>
        <div
          className="resize-handle vertical"
          onPointerDown={(event) => startHorizontalResize(event, "assistant")}
          role="separator"
          aria-label="Resize AI panel"
        />

        <aside className="assistant-panel">
          <div className="panel-header">
            <h2>AI Collaborator</h2>
            <p>Constrained to candidate-visible context and one focused issue at a time.</p>
          </div>
          <div className="assistant-chat">
            <div className="chat-messages" aria-label="AI messages" ref={chatMessagesRef}>
              {chatMessages.map((message, index) => (
                <div className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
                  <div className="chat-role">
                    <MessageSquare size={14} aria-hidden="true" />
                    <span>{message.role === "candidate" ? "You" : "Assistant"}</span>
                  </div>
                  <p>{message.content}</p>
                  {message.tags?.length ? (
                    <div className="tag-row">
                      {message.tags.map((tag) => (
                        <span className={`status-pill ${message.allowed === false ? "error" : "ready"}`} key={tag}>
                          {tag}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
            <label htmlFor="assistant-message">Ask about the selected file or public test output</label>
            <textarea
              id="assistant-message"
              value={chatInput}
              onChange={(event) => setChatInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void sendChatMessage();
                }
              }}
            />
            <button className="command-button primary" disabled={chatLoading || !chatInput.trim()} onClick={sendChatMessage}>
              <Send size={17} aria-hidden="true" />
              {chatLoading ? "Sending" : "Ask"}
            </button>
          </div>
        </aside>
      </section>

      <div
        className="resize-handle horizontal"
        onPointerDown={startVerticalResize}
        role="separator"
        aria-label="Resize test and submission panel"
      />

      <section className="bottom-panel">
        <div className="test-panel">
          <div className="section-title">
            <h2>Public Test Output</h2>
            {testResult ? (
              <span className={`status-pill ${statusClass(testResult.status)}`}>{testResult.status}</span>
            ) : null}
          </div>
          {testResult && attempt.assessment.seeded_issue_count > 0 ? (
            <p className="submission-help">
              Note: {attempt.assessment.seeded_issue_count} additional behaviors are evaluated beyond these public tests.
            </p>
          ) : null}
          {publicRunMessage ? <p className="operation-status">{publicRunMessage}</p> : null}
          <pre className="output">{resultText(testResult, testError)}</pre>
        </div>

        <div className="submission-panel" ref={submissionPanelRef}>
          <div className="section-title">
            <h2>Final Submission</h2>
            {submitted ? (
              <span className="status-pill ready">
                <ClipboardCheck size={13} aria-hidden="true" /> Recorded
              </span>
            ) : null}
          </div>
          {!submitted ? (
            <p className="submission-help">
              Submission review is supporting evidence. If time expires, the current browser files are submitted automatically.
            </p>
          ) : null}
          {submissionResult ? (
            <p className="submission-status">
              {submissionResult.hidden_test_status === "passed"
                ? "All hidden tests passed."
                : "Some hidden tests failed."}
            </p>
          ) : null}
          {submissionMessage ? <p className="operation-status">{submissionMessage}</p> : null}
          {submitError ? <p className="submission-error">{submitError}</p> : null}
          {saveStatus ? <p className="submission-status">{saveStatus}</p> : null}
          <div className="submission-grid">
            <label htmlFor="review-changed">What did you change?</label>
            <textarea
              id="review-changed"
              ref={submissionReviewRef}
              placeholder="Summarize the concrete implementation changes."
              value={submissionReview.changed}
              disabled={submitted}
              onChange={(event) => setSubmissionReview((current) => ({ ...current, changed: event.target.value }))}
            />
            <label htmlFor="review-tradeoffs">What tradeoffs or product decisions did you make?</label>
            <textarea
              id="review-tradeoffs"
              placeholder="Explain important choices, ambiguity, and authorization/status policies."
              value={submissionReview.tradeoffs}
              disabled={submitted}
              onChange={(event) => setSubmissionReview((current) => ({ ...current, tradeoffs: event.target.value }))}
            />
            <label htmlFor="review-verification">How did you verify your changes?</label>
            <textarea
              id="review-verification"
              placeholder="Mention public tests, candidate tests, manual checks, and remaining risk."
              value={submissionReview.verification}
              disabled={submitted}
              onChange={(event) => setSubmissionReview((current) => ({ ...current, verification: event.target.value }))}
            />
            <label htmlFor="review-next">What would you improve next, given more time?</label>
            <textarea
              id="review-next"
              placeholder="Name the next highest-value improvement or test coverage gap."
              value={submissionReview.nextSteps}
              disabled={submitted}
              onChange={(event) => setSubmissionReview((current) => ({ ...current, nextSteps: event.target.value }))}
            />
            <label htmlFor="review-notes">Optional: anything else the evaluator should know?</label>
            <textarea
              id="review-notes"
              placeholder="Optional context."
              value={submissionReview.notes}
              disabled={submitted}
              onChange={(event) => setSubmissionReview((current) => ({ ...current, notes: event.target.value }))}
            />
          </div>
        </div>
      </section>
      {confirmingSubmit ? (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-modal" role="dialog" aria-modal="true" aria-labelledby="submit-confirm-title">
            <h2 id="submit-confirm-title">Submit final attempt?</h2>
            <p>Submission is permanent. Hidden tests run only after this step.</p>
            <ul className="submit-checklist">
              <li><strong>Public tests run:</strong> {publicTestsRun ? "yes" : "no"}</li>
              <li><strong>Candidate tests added or updated:</strong> {candidateTestsAdded ? "yes" : "no"}</li>
              <li><strong>Submission review answered:</strong> {reviewAnsweredCount}/4 required questions</li>
            </ul>
            <div className="modal-actions">
              <button className="command-button secondary" onClick={() => setConfirmingSubmit(false)}>Cancel</button>
              <button className="command-button primary" disabled={submitting} onClick={() => submitFinal()}>
                <Send size={17} aria-hidden="true" />
                Submit final
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}
