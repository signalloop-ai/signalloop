"use client";

import Editor from "@monaco-editor/react";
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
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
  evaluator_feedback_mode: "strict" | "guided";
  duration_minutes: number;
  started_at: string | null;
  expires_at: string | null;
  submitted_at: string | null;
  submission_mode: string | null;
  files: Record<string, string>;
  initial_files: Record<string, string>;
};

type TestResult = {
  status: "passed" | "failed" | "error" | "timeout";
  exit_code: number | null;
  stdout: string;
  stderr: string;
  duration_ms: number;
  timings?: Record<string, number>;
  evaluator_feedback?: {
    mode: "guided";
    status: string;
    collected: number;
    passed: number;
    failed: number;
    details_hidden: boolean;
  } | null;
  enhancement_feedback?: {
    passed: number;
    failed: number;
    collected: number;
  } | null;
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

type EditorHandle = {
  focus: () => void;
  getModel: () => unknown;
  revealLineInCenter: (lineNumber: number) => void;
  setPosition: (position: { lineNumber: number; column: number }) => void;
};

type DiagnosticMarker = {
  severity: number;
  message: string;
  startLineNumber: number;
  startColumn: number;
  endLineNumber: number;
  endColumn: number;
};

type MonacoHandle = {
  MarkerSeverity: { Error: number; Warning: number };
  editor: {
    setModelMarkers: (model: unknown, owner: string, markers: DiagnosticMarker[]) => void;
  };
};

type SyntaxDiagnostic = {
  path: string;
  lineNumber: number;
  message: string;
  severity: "error" | "warning";
};

type OutputReference = {
  file: string;
  lineNumber: number;
};

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

function diagnosticsForPython(path: string, content: string): SyntaxDiagnostic[] {
  if (!path.endsWith(".py")) return [];

  const diagnostics: SyntaxDiagnostic[] = [];
  const stack: Array<{ char: string; lineNumber: number; column: number }> = [];
  const pairs: Record<string, string> = { "(": ")", "[": "]", "{": "}" };
  const closing = new Set(Object.values(pairs));
  const lines = content.split("\n");

  lines.forEach((line, index) => {
    const lineNumber = index + 1;
    let inSingle = false;
    let inDouble = false;

    for (let columnIndex = 0; columnIndex < line.length; columnIndex += 1) {
      const char = line[columnIndex];
      const prev = line[columnIndex - 1];
      if (char === "'" && prev !== "\\" && !inDouble) inSingle = !inSingle;
      if (char === "\"" && prev !== "\\" && !inSingle) inDouble = !inDouble;
      if (inSingle || inDouble) continue;
      if (pairs[char]) stack.push({ char, lineNumber, column: columnIndex + 1 });
      if (closing.has(char)) {
        const last = stack.pop();
        if (!last || pairs[last.char] !== char) {
          diagnostics.push({
            path,
            lineNumber,
            message: `Unexpected closing ${char}`,
            severity: "error",
          });
        }
      }
    }

    const stripped = line.trim();
    const needsColon = /^(async\s+def|def|class|if|elif|else|for|while|try|except|finally|with)\b/.test(stripped);
    if (needsColon && !stripped.endsWith(":") && !stripped.endsWith("\\")) {
      diagnostics.push({
        path,
        lineNumber,
        message: "Possible missing ':' at the end of this Python block.",
        severity: "warning",
      });
    }
  });

  stack.forEach((item) => {
    diagnostics.push({
      path,
      lineNumber: item.lineNumber,
      message: `Unclosed ${item.char}`,
      severity: "error",
    });
  });

  return diagnostics;
}

function outputLineClass(line: string): string {
  if (/FAILED|ERROR|AssertionError|Traceback| E\s+/.test(line)) return "error";
  if (/PASSED|\spassed\b|\[100%\]/.test(line)) return "passed";
  if (/warning|skipped|timeout/i.test(line)) return "warn";
  return "neutral";
}

function findOutputReference(line: string, files: Record<string, string>): OutputReference | null {
  const match = line.match(/((?:task_api|tests)\/[A-Za-z0-9_./-]+\.py):(\d+)/);
  if (!match) return null;
  const file = match[1];
  if (!(file in files)) return null;
  return { file, lineNumber: Number(match[2]) };
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
  const [runElapsed, setRunElapsed] = useState(0);
  const [submitElapsed, setSubmitElapsed] = useState(0);
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
  const [filePanelWidth, setFilePanelWidth] = useState(220);
  const [assistantPanelWidth, setAssistantPanelWidth] = useState(320);
  const [bottomPanelHeight, setBottomPanelHeight] = useState(260);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const [editorMounted, setEditorMounted] = useState(false);
  const [whatToDoCollapsed, setWhatToDoCollapsed] = useState(false);
  const [testDrawerOpen, setTestDrawerOpen] = useState(false);

  const chatMessagesRef = useRef<HTMLDivElement | null>(null);
  const autoSnapshotTimeoutRef = useRef<number | null>(null);
  const editorRef = useRef<EditorHandle | null>(null);
  const monacoRef = useRef<MonacoHandle | null>(null);
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
        setInitialFiles(body.initial_files ?? body.files);
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

  useEffect(() => {
    if (!running) { setRunElapsed(0); return; }
    setRunElapsed(0);
    const id = setInterval(() => setRunElapsed((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [running]);

  useEffect(() => {
    if (!submitting) { setSubmitElapsed(0); return; }
    setSubmitElapsed(0);
    const id = setInterval(() => setSubmitElapsed((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [submitting]);

  // Auto-expand test output drawer when results arrive
  useEffect(() => {
    if (testResult || testError) setTestDrawerOpen(true);
  }, [testResult, testError]);

  const sortedFiles = useMemo(() => Object.keys(files).sort(), [files]);
  const activeContent = activePath ? files[activePath] ?? "" : "";
  const syntaxDiagnostics = useMemo(
    () => diagnosticsForPython(activePath, activeContent),
    [activePath, activeContent],
  );
  const testOutputText = useMemo(() => resultText(testResult, testError), [testResult, testError]);

  const outputLineAnnotations = useMemo(() => {
    const lines = testOutputText.split("\n");
    const failureLineId: Record<string, string> = {};
    let summaryStartIndex = -1;

    lines.forEach((line, i) => {
      const headerMatch = line.match(/^_{4,}\s+(\S+)\s+_{4,}/);
      if (headerMatch) failureLineId[headerMatch[1]] = `output-failure-${i}`;
      if (line.includes("short test summary info")) summaryStartIndex = i;
    });

    return { failureLineId, summaryStartIndex };
  }, [testOutputText]);

  const filesWithOutputReferences = useMemo(() => {
    const referenced = new Set<string>();
    for (const line of testOutputText.split("\n")) {
      const ref = findOutputReference(line, files);
      if (ref) referenced.add(ref.file);
    }
    return referenced;
  }, [files, testOutputText]);

  const filesWithDiagnostics = useMemo(() => {
    const referenced = new Set<string>();
    for (const diagnostic of syntaxDiagnostics) {
      referenced.add(diagnostic.path);
    }
    return referenced;
  }, [syntaxDiagnostics]);

  const reviewAnsweredCount = submissionReview.changed.trim().length > 0 ? 1 : 0;
  const candidateTestsAdded = useMemo(
    () => Object.keys(files).some((path) => path.startsWith("tests/") && files[path] !== initialFiles[path]),
    [files, initialFiles],
  );
  const candidateTestCount = useMemo(() => {
    const countTests = (content: string) => (content.match(/^def test_/gm) ?? []).length;
    const currentTotal = Object.entries(files)
      .filter(([p]) => p.startsWith("tests/"))
      .reduce((n, [p, c]) => n + countTests(c), 0);
    const initialTotal = Object.entries(initialFiles)
      .filter(([p]) => p.startsWith("tests/"))
      .reduce((n, [p, c]) => n + countTests(c), 0);
    return currentTotal - initialTotal;
  }, [files, initialFiles]);

  const publicTestsRun = testResult !== null || testError !== null;
  const canSubmit = !submitted && !submitting;
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

  // Progress values for topbar chips
  const progressPassed = Number(testResult?.stdout?.match(/(\d+) passed/)?.[1] ?? 0);
  const progressFailed = Number(testResult?.stdout?.match(/(\d+) failed/)?.[1] ?? 0);
  const progressAllPass = testResult?.status === "passed";

  // Collapse bottom panel to header-only height when test drawer is closed
  const effectiveBottomHeight = testDrawerOpen ? bottomPanelHeight : 50;

  const publicRunMessage = running ? `Running tests… ${runElapsed}s` : null;
  const submissionMessage = submitting ? `Submitting… ${submitElapsed}s` : null;

  function openFileAtLine(path: string, lineNumber: number) {
    setActivePath(path);
    window.setTimeout(() => {
      editorRef.current?.setPosition({ lineNumber, column: 1 });
      editorRef.current?.revealLineInCenter(lineNumber);
      editorRef.current?.focus();
    }, 0);
  }

  useEffect(() => {
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    const model = editor?.getModel();
    if (!editor || !monaco || !model) return;
    const markers = syntaxDiagnostics.map((diagnostic) => ({
      severity: diagnostic.severity === "error" ? monaco.MarkerSeverity.Error : monaco.MarkerSeverity.Warning,
      message: diagnostic.message,
      startLineNumber: diagnostic.lineNumber,
      startColumn: 1,
      endLineNumber: diagnostic.lineNumber,
      endColumn: 120,
    }));
    monaco.editor.setModelMarkers(model, "signalloop-python-diagnostics", markers);
  }, [syntaxDiagnostics, editorMounted]);

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
        setFilePanelWidth(Math.min(420, Math.max(160, startWidth + delta)));
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
      setBottomPanelHeight(Math.min(480, Math.max(200, startHeight + delta)));
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
      setSaveStatus(kind === "autosave" ? "Auto-saved" : "Saved before test run");
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
      setInitialFiles(body.initial_files ?? body.files);
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
      submissionReview.changed.trim() ? `What changed: ${submissionReview.changed.trim()}` : "",
      submissionReview.notes.trim() ? `Additional notes: ${submissionReview.notes.trim()}` : "",
    ].filter(Boolean).join("\n\n") || "Not answered.";
    const decisionLog = "";
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
            ? { path: activePath, content: files[activePath] ?? "" }
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
          "--bottom-panel-height": `${effectiveBottomHeight}px`,
        } as CSSProperties
      }
    >
      {/* ── TOPBAR ── */}
      <header className="topbar">
        <div className="topbar-title">
          <svg className="topbar-logo" width="30" height="30" viewBox="0 0 30 30" fill="none" aria-label="SignalLoop">
            <rect width="30" height="30" rx="7" fill="#0f766e"/>
            <path d="M15 6C19.97 6 24 10.03 24 15C24 19.97 19.97 24 15 24C10.5 24 6.8 20.7 6.1 16.4" stroke="white" strokeWidth="2.3" strokeLinecap="round"/>
            <path d="M4.5 14.5L6.2 17.2L9 15.5" stroke="white" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round"/>
            <circle cx="15" cy="6" r="2" fill="#5eead4"/>
          </svg>
          <div>
            <h1>{attempt.assessment.title}</h1>
            <p>SignalLoop · Attempt #{attempt.attempt_id} · {attempt.candidate_email ?? "candidate invite"} · {attempt.assessment.version}</p>
          </div>
        </div>

        <div className="topbar-actions">
          {/* Grouped status & state box */}
          <div className="status-box">
            <span className={`status-pill ${submitted ? "ready" : isExpired ? "error" : statusClass(attempt.status)}`}>
              {submitted ? "submitted" : isExpired ? "expired" : attempt.status}
            </span>
            {isTimed && !submitted && msRemaining !== null ? (
              <span className={`status-pill ${isExpired ? "error" : timerWarning ? "warn" : "ready"}`}>
                {isExpired ? "Expired" : `Time ${formatCountdown(msRemaining)}`}
              </span>
            ) : null}
            {isTimed && submitted && isExpired ? <span className="status-pill error">Expired</span> : null}
            {!isTimed ? <span className="status-pill ready">Recommended {attempt.duration_minutes}m</span> : null}
            {timerWarning && !isExpired ? <span className="status-pill warn">{timerWarning}</span> : null}
            {submissionResult ? (
              <span className={`status-pill ${submissionResult.hidden_test_status === "passed" ? "ready" : "warn"}`}>
                {submissionResult.hidden_test_status === "passed" ? "All hidden tests passed" : "Some hidden tests failed"}
              </span>
            ) : null}
            {publicRunMessage ? <span className="operation-status">{publicRunMessage}</span> : null}
            {submissionMessage ? <span className="operation-status">{submissionMessage}</span> : null}
          </div>
          <button className="command-button primary" disabled={running || submitted} onClick={runPublicTests}>
            <Play size={17} aria-hidden="true" />
            {running ? "Running" : "Run Tests"}
          </button>
          <button className="command-button primary" disabled={submitted} onClick={() => setConfirmingSubmit(true)}>
            <Send size={17} aria-hidden="true" />
            Submit
          </button>
        </div>
      </header>

      {/* ── WORKSPACE GRID ── */}
      <section className="workspace-grid">

        {/* LEFT — IDE File Explorer */}
        <aside className="sidebar">
          <div className="explorer-header">
            <span>EXPLORER</span>
            {saveStatus ? <span className="autosave-chip">{saveStatus}</span> : null}
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
                {filesWithDiagnostics.has(path) ? <span className="file-marker error" title="Syntax diagnostics">!</span> : null}
                {filesWithOutputReferences.has(path) ? <span className="file-marker warn" title="Referenced in public output">↗</span> : null}
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

        {/* CENTER — Monaco Editor */}
        <section className="editor-zone">
          <div className="editor-tabs">
            <div className="active-file" title={activePath}>
              <FolderTree size={16} aria-hidden="true" />
              <span>{activePath || "No file selected"}</span>
            </div>
            <span className="editor-autosave">
              {saveStatus || "Files auto-saved every 60s"}
            </span>
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
              onMount={(editor, monaco) => {
                editorRef.current = editor;
                monacoRef.current = monaco;
                setEditorMounted(true);
              }}
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

        {/* RIGHT — What to do + AI Collaborator */}
        <aside className="assistant-panel">
          <div className="what-to-do">
            <button
              className="what-to-do-header"
              onClick={() => setWhatToDoCollapsed((c) => !c)}
              aria-expanded={!whatToDoCollapsed}
            >
              <span>What to do</span>
              {whatToDoCollapsed
                ? <ChevronRight size={14} aria-hidden="true" />
                : <ChevronDown size={14} aria-hidden="true" />}
            </button>
            {!whatToDoCollapsed && (
              <div className="what-to-do-body">
                <ol>
                  <li>
                    Read{" "}
                    {"README.md" in files ? (
                      <button className="inline-link" onClick={() => setActivePath("README.md")}>README.md</button>
                    ) : "README.md"}{" "}
                    — scenario, bugs, and enhancements are all described there.
                  </li>
                  <li>Fix the failing public tests — click <strong>Run Tests</strong> to see which fail.</li>
                  <li>Find and fix hidden issues by reading the code — <strong>how</strong> you fix matters: design decisions (e.g., 403 vs 404) are evaluated, not just whether a test passes.</li>
                  <li>Implement the enhancements described in README.md — edge cases and validation correctness are evaluated, not just the happy path.</li>
                  <li>Write test cases for your fixes and enhancements.</li>
                  <li>Click <strong>Submit</strong> in the top bar when done.</li>
                </ol>
              </div>
            )}
          </div>

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

      {/* ── RESIZE HANDLE ── */}
      <div
        className="resize-handle horizontal"
        onPointerDown={startVerticalResize}
        role="separator"
        aria-label="Resize bottom panel"
      />

      {/* ── BOTTOM PANEL ── */}
      <section className="bottom-panel">

        {/* Test Output Drawer */}
        <div className="test-panel">
          <div className="section-title">
            <h2>Public Test Output</h2>
            <div className="drawer-title-end">
              {testResult ? (() => {
                const total = progressPassed + progressFailed;
                const label = total > 0
                  ? progressFailed > 0
                    ? `${progressFailed}/${total} failed`
                    : `${total}/${total} passed`
                  : testResult.status;
                return (
                  <span className={`status-pill ${progressFailed > 0 ? "error" : "ready"}`}>{label}</span>
                );
              })() : running ? (
                <span className="status-pill warn">running…</span>
              ) : null}
              <button
                className="icon-button"
                onClick={() => setTestDrawerOpen((o) => !o)}
                title={testDrawerOpen ? "Collapse" : "Expand"}
              >
                {testDrawerOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              </button>
            </div>
          </div>
          {testDrawerOpen && (
            <>
              {testResult && (
                <p className="autosave-note">File paths in the output are clickable — click to jump to that line in the editor.</p>
              )}
              {publicRunMessage ? <p className="operation-status">{publicRunMessage}</p> : null}
              {testResult?.timings?.api_total_ms ? (
                <p className="submission-help">Completed in {Math.round(testResult.timings.api_total_ms / 1000)}s.</p>
              ) : testResult ? (
                <p className="submission-help">Completed in {Math.round(testResult.duration_ms / 1000)}s.</p>
              ) : null}
              <div id="test-output" className="output" role="log" aria-label="Public test output">
                {testOutputText.split("\n").map((line, index) => {
                  const ref = findOutputReference(line, files);
                  const { failureLineId, summaryStartIndex } = outputLineAnnotations;

                  const headerMatch = line.match(/^_{4,}\s+(\S+)\s+_{4,}/);
                  const lineId = headerMatch ? failureLineId[headerMatch[1]] : undefined;

                  const inSummary = summaryStartIndex >= 0 && index > summaryStartIndex;
                  const summaryMatch = inSummary ? line.match(/^FAILED\s+[^:]+::(\S+?)(?:\s|$)/) : null;
                  const summaryTargetId = summaryMatch ? failureLineId[summaryMatch[1]] : undefined;

                  return (
                    <div
                      id={lineId}
                      className={`output-line ${outputLineClass(line)}`}
                      key={`${index}-${line}`}
                    >
                      {summaryTargetId ? (
                        <a
                          href={`#${summaryTargetId}`}
                          className="output-link"
                          onClick={(e) => {
                            e.preventDefault();
                            document.getElementById(summaryTargetId)?.scrollIntoView({ behavior: "smooth", block: "start" });
                          }}
                        >
                          {line || " "}
                        </a>
                      ) : ref ? (
                        <button className="output-link" onClick={() => openFileAtLine(ref.file, ref.lineNumber)}>
                          {line || " "}
                        </button>
                      ) : (
                        <span>{line || " "}</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>

      </section>

      {/* ── SUBMIT MODAL ── */}
      {confirmingSubmit ? (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-modal" role="dialog" aria-modal="true" aria-labelledby="submit-confirm-title">
            <h2 id="submit-confirm-title">Submit final attempt?</h2>
            <p>Submission is permanent. Review your progress, add notes, then confirm.</p>

            {/* Status summary */}
            <div className="submit-status">
              {(() => {
                const total = progressPassed + progressFailed;
                const allPass = progressAllPass;
                const someRun = publicTestsRun;
                return (
                  <div className="submit-status-item">
                    <span className={`submit-status-icon ${someRun ? (allPass ? "done" : "partial") : ""}`}>
                      {someRun ? (allPass ? "✓" : "◑") : "○"}
                    </span>
                    <div>
                      <strong>Public tests</strong>
                      <span>{someRun ? (total > 0 ? `${progressPassed} passed${progressFailed ? `, ${progressFailed} failed` : ""}` : testResult?.status) : "Not run yet"}</span>
                      <em>Shown during the assessment — all should pass before submitting</em>
                    </div>
                  </div>
                );
              })()}
              {attempt.evaluator_feedback_mode === "guided" ? (() => {
                const hf = testResult?.evaluator_feedback;
                const ef = testResult?.enhancement_feedback;
                const hasResult = hf != null;
                const edgePassed = hasResult ? Math.max(0, hf!.passed - (ef?.passed ?? 0)) : 0;
                const edgeFailed = hasResult ? Math.max(0, hf!.failed - (ef?.failed ?? 0)) : 0;
                return (
                  <div className="submit-status-item">
                    <span className={`submit-status-icon ${hasResult ? (edgeFailed === 0 ? "done" : "partial") : ""}`}>
                      {hasResult ? (edgeFailed === 0 ? "✓" : "◑") : "○"}
                    </span>
                    <div>
                      <strong>Hidden checks</strong>
                      <span>{hasResult ? `${edgePassed} passed${edgeFailed ? `, ${edgeFailed} failing` : ""}` : "Run tests to check"}</span>
                      <em>Edge cases and policy correctness beyond the public tests</em>
                    </div>
                  </div>
                );
              })() : null}
              {(() => {
                const ef = testResult?.enhancement_feedback;
                const hasResult = (ef?.collected ?? 0) > 0;
                return (
                  <div className="submit-status-item">
                    <span className={`submit-status-icon ${hasResult ? (ef!.failed === 0 ? "done" : "partial") : ""}`}>
                      {hasResult ? (ef!.failed === 0 ? "✓" : "◑") : "○"}
                    </span>
                    <div>
                      <strong>Enhancements</strong>
                      <span>{hasResult ? `${ef!.passed}/${ef!.collected} passing` : "Run tests to check"}</span>
                      <em>New features described in README.md — edge cases evaluated</em>
                    </div>
                  </div>
                );
              })()}
              <div className="submit-status-item">
                <span className={`submit-status-icon ${candidateTestsAdded ? "done" : ""}`}>
                  {candidateTestsAdded ? "✓" : "○"}
                </span>
                <div>
                  <strong>Candidate tests</strong>
                  <span>{candidateTestsAdded ? `${candidateTestCount} written` : "None added yet"}</span>
                  <em>Tests you wrote for your fixes and enhancements — scored at submission</em>
                </div>
              </div>
            </div>

            {/* Notes input */}
            <div className="submit-notes">
              <div className="submission-grid">
                <label htmlFor="modal-review-changed">What did you change? Any decisions or tradeoffs? <span className="submit-optional">(optional)</span></label>
                <textarea
                  id="modal-review-changed"
                  autoFocus
                  placeholder="Summarize the changes you made, any authorization or status policies you chose, and how you verified them."
                  value={submissionReview.changed}
                  disabled={submitting}
                  onChange={(event) => setSubmissionReview((current) => ({ ...current, changed: event.target.value }))}
                />
                <label htmlFor="modal-review-notes">Feedback about this assessment, or any issues you faced? <span className="submit-optional">(optional)</span></label>
                <textarea
                  id="modal-review-notes"
                  placeholder="Optional: anything the evaluator should know, or feedback about the assignment itself."
                  value={submissionReview.notes}
                  disabled={submitting}
                  onChange={(event) => setSubmissionReview((current) => ({ ...current, notes: event.target.value }))}
                />
              </div>
            </div>

            {submitError ? <p className="submission-error">{submitError}</p> : null}
            {submissionMessage ? <p className="operation-status">{submissionMessage}</p> : null}

            <div className="modal-actions">
              <button className="command-button secondary" onClick={() => setConfirmingSubmit(false)} disabled={submitting}>Cancel</button>
              <button className="command-button primary" disabled={!canSubmit} onClick={() => submitFinal()}>
                <Send size={17} aria-hidden="true" />
                {submitting ? "Submitting…" : "Submit final"}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}
