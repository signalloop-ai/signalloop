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
import { useEffect, useMemo, useRef, useState } from "react";

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
  const [finalExplanation, setFinalExplanation] = useState("");
  const [decisionLog, setDecisionLog] = useState("");
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
  const finalExplanationRef = useRef<HTMLTextAreaElement | null>(null);
  const submissionPanelRef = useRef<HTMLDivElement | null>(null);
  const chatMessagesRef = useRef<HTMLDivElement | null>(null);
  const autoSnapshotTimeoutRef = useRef<number | null>(null);

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
        setActivePath(Object.keys(body.files).sort()[0] ?? "");
        setSubmitted(body.status === "submitted");
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

  const sortedFiles = useMemo(() => Object.keys(files).sort(), [files]);
  const activeContent = activePath ? files[activePath] ?? "" : "";
  const canSubmit = !submitted && finalExplanation.trim().length > 0;

  function focusSubmission() {
    setBottomPanelHeight((current) => Math.max(current, 300));
    window.setTimeout(() => finalExplanationRef.current?.focus(), 0);
  }

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

  async function submitFinal() {
    if (!canSubmit) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const response = await fetch(`${apiBaseUrl}/candidate/invites/${inviteToken}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          files,
          final_explanation: finalExplanation,
          decision_log: decisionLog,
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
      setAttempt((current) => (current ? { ...current, status: body.status } : current));
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  }

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
          <button className="command-button primary" onClick={() => setAccepted(true)}>
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
          {submissionResult ? (
            <span className="submission-status">
              {submissionResult.hidden_test_status === "passed"
                ? "All hidden tests passed."
                : "Some hidden tests failed."}
            </span>
          ) : null}
          <button className="command-button primary" disabled={running || submitted} onClick={runPublicTests}>
            <Play size={17} aria-hidden="true" />
            {running ? "Running" : "Run Tests"}
          </button>
          <button className="command-button secondary" onClick={focusSubmission}>
            <ClipboardCheck size={17} aria-hidden="true" />
            Submission
          </button>
          <button className="command-button primary" disabled={!canSubmit || submitting} onClick={submitFinal}>
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
              <li>Fill explanation and decision log, then submit.</li>
            </ol>
            <p>Tests do not need to pass before submission. Explanation and decision log are optional but count for 5 points.</p>
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
              Final explanation is required. Decision log is optional. Tests do not need to pass before submitting.
            </p>
          ) : null}
          {submissionResult ? (
            <p className="submission-status">
              {submissionResult.hidden_test_status === "passed"
                ? "All hidden tests passed."
                : "Some hidden tests failed."}
            </p>
          ) : null}
          {submitError ? <p className="submission-error">{submitError}</p> : null}
          {saveStatus ? <p className="submission-status">{saveStatus}</p> : null}
          <div className="submission-grid">
            <label htmlFor="final-explanation">Final explanation <span aria-hidden="true" style={{ color: "var(--accent-red, #e05)" }}>*</span></label>
            <textarea
              id="final-explanation"
              ref={finalExplanationRef}
              placeholder="What did you change, what remains risky, and how did you verify?"
              value={finalExplanation}
              disabled={submitted}
              onChange={(event) => setFinalExplanation(event.target.value)}
            />
            <label htmlFor="decision-log">Decision log</label>
            <textarea
              id="decision-log"
              placeholder="Record key choices, tradeoffs, and ambiguous behavior decisions."
              value={decisionLog}
              disabled={submitted}
              onChange={(event) => setDecisionLog(event.target.value)}
            />
          </div>
        </div>
      </section>
    </main>
  );
}
