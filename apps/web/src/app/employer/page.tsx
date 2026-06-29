"use client";

import { SignInButton, UserButton, useAuth, useUser } from "@clerk/nextjs";
import {
  Activity, BarChart3, BookOpen, Brain, Bug, ChevronDown, ClipboardCopy, ClipboardList, Clock, Code2,
  Database, ExternalLink, FileText, HelpCircle, Info, Languages, LayoutDashboard, Loader2, LogIn,
  Network, Plus, Puzzle, Settings, ShieldCheck, UserCircle, Users, X,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  approveAndInviteFromBlueprint,
  createInvite,
  extractDocumentText,
  fetchAdaptiveBlueprints,
  fetchAttempts,
  generateAdaptiveBlueprint,
  type AdaptiveBuilderInput,
  type AuthTokenProvider,
  type InviteConfiguration,
} from "./api";
import { fetchEmployerMe } from "../admin/api";
import type { AssessmentBlueprint, EmployerAttemptSummary } from "./types";

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

// ── Roadmap module types (shown as "Coming soon" — not yet supported) ──────────
// Coding is the only live module today; these preview what is planned so employers
// can see the direction. They are not selectable.

const COMING_SOON_MODULES = [
  { name: "Debugging & code review", icon: Bug, color: "var(--red)", bg: "var(--red-bg)", tags: ["Bug tracing", "Root cause"], desc: "Real codebases with planted bugs. Tests the ability to read, trace, and fix unfamiliar code under time pressure." },
  { name: "System design", icon: Network, color: "var(--purple)", bg: "var(--purple-bg)", tags: ["Architecture", "Scalability"], desc: "Architecture and scalability questions probed adaptively. Tests distributed-systems depth and trade-off reasoning." },
  { name: "AI & LLM awareness", icon: Brain, color: "var(--cyan)", bg: "var(--cyan-bg)", tags: ["ML fundamentals", "Prompt design"], desc: "Conceptual ML, prompt engineering, and responsible AI use beyond surface-level familiarity." },
  { name: "SQL & data querying", icon: Database, color: "var(--orange)", bg: "var(--orange-bg)", tags: ["Queries", "Optimisation"], desc: "Write, optimise, and debug SQL against realistic schemas, from simple joins to multi-CTE query planning." },
  { name: "Logical reasoning", icon: Puzzle, color: "var(--amber)", bg: "var(--amber-bg)", tags: ["Patterns", "Deduction"], desc: "Abstract pattern recognition and structured analytical thinking with adaptive branching." },
  { name: "Psychometric profile", icon: UserCircle, color: "var(--green)", bg: "var(--green-bg)", tags: ["OCEAN", "Values fit"], desc: "Big Five and situational-judgement tests calibrated to engineering role archetypes." },
  { name: "Communication & language", icon: Languages, color: "var(--indigo)", bg: "var(--indigo-bg)", tags: ["Writing", "Clarity"], desc: "Written clarity, business English, and language comprehension calibrated to proficiency levels." },
] as const;

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
    <rect width="30" height="30" rx="7" fill="#3b82f6" />
    <path d="M15 6C19.97 6 24 10.03 24 15C24 19.97 19.97 24 15 24C10.5 24 6.8 20.7 6.1 16.4" stroke="white" strokeWidth="2.3" strokeLinecap="round" />
    <path d="M4.5 14.5L6.2 17.2L9 15.5" stroke="white" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="15" cy="6" r="2" fill="#22d3ee" />
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

function CreationPathsOverview() {
  return (
    <section className="creation-paths-overview" aria-labelledby="creation-paths-heading">
      <div className="section-title">
        <h2 id="creation-paths-heading" style={{ fontSize: 15 }}>Assessment creation paths</h2>
      </div>
      <div className="creation-path-grid">
        <div className="creation-path-card">
          <span className="creation-path-icon"><Code2 size={18} aria-hidden="true" /></span>
          <div>
            <h3>Direct coding challenge</h3>
            <p>Manually choose Standard or Advanced FastAPI, set timing and feedback, then send the candidate invite.</p>
          </div>
        </div>
        <div className="creation-path-card adaptive">
          <span className="creation-path-icon"><Brain size={18} aria-hidden="true" /></span>
          <div>
            <h3>Adaptive builder</h3>
            <p>Paste or upload the JD and resume. SignalLoop recommends a blueprint, shows future coverage, and creates the invite after approval.</p>
          </div>
        </div>
      </div>
    </section>
  );
}

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
              <h3>Choose a creation path</h3>
              <p>Start from the Assessments view with either direct setup or adaptive blueprint generation:</p>
              <ul>
                <li><strong>Direct coding challenge</strong> — manually choose Standard or Advanced FastAPI</li>
                <li><strong>Adaptive builder</strong> — paste or upload the JD/resume, review the generated blueprint, then approve the invite</li>
                <li><strong>Settings</strong> — timing and evaluator feedback still apply to either path</li>
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
                <li>Role-adaptive context for blueprint-backed attempts</li>
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

function skillLabel(skillId: string): string {
  return skillId.replaceAll("_", " ").replaceAll(".", " / ");
}

function uniqueSkills(skills: Array<string | undefined>): string[] {
  return Array.from(new Set(skills.filter((skill): skill is string => Boolean(skill))));
}

function SkillPills({ title, skills, tone = "default" }: { title: string; skills?: string[]; tone?: "default" | "warn" | "ready" }) {
  const visibleSkills = uniqueSkills(skills ?? []);
  if (!visibleSkills.length) return null;
  return (
    <div className="assessment-section" style={{ marginTop: 12 }}>
      <div className="assessment-section-header">{title}</div>
      <div className="mod-tags">
        {visibleSkills.slice(0, 12).map((skill) => (
          <span className={`mod-tag ${tone === "warn" ? "warn" : tone === "ready" ? "ready" : ""}`} key={skill}>
            {skillLabel(skill)}
          </span>
        ))}
      </div>
    </div>
  );
}

function blueprintStatusMeta(blueprint: AssessmentBlueprint, selected: boolean) {
  if (blueprint.assessment_pack_slug.startsWith("future_")) {
    return {
      dot: "var(--amber)",
      label: "Future",
      pillClass: "warn",
      action: selected ? "Selected" : "Select",
    };
  }
  if (blueprint.status === "used") {
    return {
      dot: "var(--green)",
      label: "Invite sent",
      pillClass: "ready",
      action: selected ? "Selected" : "Review",
    };
  }
  return {
    dot: "var(--blue)",
    label: "Draft",
    pillClass: "",
    action: selected ? "Selected" : "Select",
  };
}

function AdaptiveBuilder({
  getAuthToken,
  onCreated,
}: {
  getAuthToken: AuthTokenProvider;
  onCreated: (attempts: EmployerAttemptSummary[], inviteUrl: string | null) => void;
}) {
  const [roleTitle, setRoleTitle] = useState("Senior Backend Engineer");
  const [roleFamily, setRoleFamily] = useState<AdaptiveBuilderInput["roleFamily"]>("backend");
  const [seniority, setSeniority] = useState<AdaptiveBuilderInput["seniority"]>("senior");
  const [expectedAiUsage, setExpectedAiUsage] = useState(70);
  const [candidateEmail, setCandidateEmail] = useState("");
  const [jdText, setJdText] = useState("");
  const [teamContext, setTeamContext] = useState("");
  const [resumeText, setResumeText] = useState("");
  const [timingMode, setTimingMode] = useState<InviteConfiguration["timingMode"]>("timed");
  const [evaluatorFeedbackMode, setEvaluatorFeedbackMode] = useState<InviteConfiguration["evaluatorFeedbackMode"]>("strict");
  const [blueprint, setBlueprint] = useState<AssessmentBlueprint | null>(null);
  const [savedBlueprints, setSavedBlueprints] = useState<AssessmentBlueprint[]>([]);
  const [adaptiveInviteUrl, setAdaptiveInviteUrl] = useState<string | null>(null);
  const [showBlueprintAssessmentDetail, setShowBlueprintAssessmentDetail] = useState<"standard" | "advanced" | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploadingField, setUploadingField] = useState<"jd" | "resume" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const emailValid = useMemo(() => (
    candidateEmail.trim().length > 0 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(candidateEmail.trim())
  ), [candidateEmail]);
  const canGenerate = roleTitle.trim().length >= 2 && jdText.trim().length >= 20 && !busy;
  const isFutureBlueprint = !!blueprint && blueprint.assessment_pack_slug.startsWith("future_");
  const canInvite = !!blueprint && !isFutureBlueprint && blueprint.status !== "used" && emailValid && !busy;

  const loadSavedBlueprints = useCallback(async () => {
    try {
      setSavedBlueprints(await fetchAdaptiveBlueprints(getAuthToken));
    } catch {
      // Saved blueprints are helpful context, not a blocker for creating a new one.
    }
  }, [getAuthToken]);

  useEffect(() => {
    void loadSavedBlueprints();
  }, [loadSavedBlueprints]);

  async function generate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const generated = await generateAdaptiveBlueprint({
        roleTitle: roleTitle.trim(),
        roleFamily,
        seniority,
        jdText: jdText.trim(),
        teamContext: teamContext.trim(),
        expectedAiUsage,
        candidateEmail: candidateEmail.trim(),
        resumeText: resumeText.trim(),
        timingMode,
        evaluatorFeedbackMode,
      }, getAuthToken);
      setBlueprint(generated);
      setSavedBlueprints((current) => [generated, ...current.filter((item) => item.id !== generated.id)].slice(0, 20));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Adaptive blueprint generation failed");
    } finally {
      setBusy(false);
    }
  }

  async function approveAndSend() {
    if (!blueprint) return;
    setBusy(true);
    setError(null);
    try {
      const result = await approveAndInviteFromBlueprint(blueprint.id, candidateEmail.trim(), getAuthToken);
      onCreated(result.attempts, result.inviteUrl);
      setAdaptiveInviteUrl(result.inviteUrl);
      setBlueprint(null);
      setCandidateEmail("");
      setResumeText("");
      await loadSavedBlueprints();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Adaptive invite creation failed");
    } finally {
      setBusy(false);
    }
  }

  function copyAdaptiveInviteUrl() {
    if (!adaptiveInviteUrl) return;
    void navigator.clipboard?.writeText(adaptiveInviteUrl);
  }

  async function uploadDocumentText(file: File | null, target: "jd" | "resume") {
    if (!file) return;
    setUploadingField(target);
    setError(null);
    try {
      const extracted = await extractDocumentText(file, getAuthToken);
      if (target === "jd") {
        setJdText(extracted.text);
      } else {
        setResumeText(extracted.text);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Document text extraction failed");
    } finally {
      setUploadingField(null);
    }
  }

  return (
    <section className="mod-card" style={{ marginBottom: 18 }}>
      <div className="mod-card-head">
        <span className="mod-icon">
          <Brain size={18} aria-hidden="true" />
        </span>
        <div>
          <p className="mod-title">Adaptive builder <span className="status-pill">Optional</span></p>
          <p className="mod-sub">Paste JD and resume text · review saved blueprint · send invite</p>
        </div>
      </div>
      <p className="mod-desc">
        Use this when you want the system to map a JD and resume to the closest supported coding assessment. You can also skip this and use the Coding challenge form below directly.
      </p>

      <form onSubmit={generate} className="report-grid" style={{ marginTop: 14 }}>
        <div>
          <div className="summary-field">
            <span className="summary-field-label">Role title</span>
            <input className="text-input" value={roleTitle} onChange={(e) => setRoleTitle(e.target.value)} />
          </div>
          <div className="summary-field">
            <span className="summary-field-label">Candidate email</span>
            <input className="text-input" type="email" value={candidateEmail} onChange={(e) => setCandidateEmail(e.target.value)} placeholder="candidate@company.com" />
          </div>
          <div className="summary-field">
            <span className="summary-field-label">Role family / seniority</span>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <select value={roleFamily} onChange={(e) => setRoleFamily(e.target.value as AdaptiveBuilderInput["roleFamily"])}>
                <option value="backend">Backend</option>
                <option value="fullstack">Full-stack</option>
                <option value="frontend">Frontend</option>
                <option value="infra">Infra</option>
                <option value="data">Data</option>
                <option value="ai">AI / ML</option>
              </select>
              <select value={seniority} onChange={(e) => setSeniority(e.target.value as AdaptiveBuilderInput["seniority"])}>
                <option value="junior">Junior</option>
                <option value="mid">Mid</option>
                <option value="senior">Senior</option>
                <option value="staff">Staff</option>
              </select>
            </div>
          </div>
          <div className="summary-field">
            <span className="summary-field-label">Expected AI usage: {expectedAiUsage}%</span>
            <input type="range" min={0} max={100} step={10} value={expectedAiUsage} onChange={(e) => setExpectedAiUsage(Number(e.target.value))} />
          </div>
        </div>

        <div>
          <div className="summary-field">
            <span className="summary-field-label">JD / role requirements</span>
            <input
              className="text-input"
              type="file"
              accept=".txt,.md,.pdf,.docx,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              aria-label="Upload JD"
              onChange={(event) => {
                void uploadDocumentText(event.target.files?.[0] ?? null, "jd");
                event.currentTarget.value = "";
              }}
            />
            {uploadingField === "jd" ? <p className="hint">Extracting JD text…</p> : null}
            <textarea className="text-input" style={{ minHeight: 120 }} value={jdText} onChange={(e) => setJdText(e.target.value)} placeholder="Paste the job description or role requirements." />
          </div>
          <div className="summary-field">
            <span className="summary-field-label">Candidate resume text</span>
            <input
              className="text-input"
              type="file"
              accept=".txt,.md,.pdf,.docx,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              aria-label="Upload resume"
              onChange={(event) => {
                void uploadDocumentText(event.target.files?.[0] ?? null, "resume");
                event.currentTarget.value = "";
              }}
            />
            {uploadingField === "resume" ? <p className="hint">Extracting resume text…</p> : null}
            <textarea className="text-input" style={{ minHeight: 96 }} value={resumeText} onChange={(e) => setResumeText(e.target.value)} placeholder="Optional for blueprint generation; recommended for follow-up probes." />
            <p className="hint">Upload TXT, DOCX, or text-based PDF. Scanned PDFs are not supported yet.</p>
          </div>
          <div className="summary-field">
            <span className="summary-field-label">Product/team context optional</span>
            <input className="text-input" value={teamContext} onChange={(e) => setTeamContext(e.target.value)} placeholder="e.g. internal workflow APIs, fintech payments, AI infrastructure" />
            <p className="hint">Extra domain or team context that may not be obvious from the JD. Leave blank if the JD is enough.</p>
          </div>
        </div>

        <div>
          <div className="summary-field">
            <span className="summary-field-label">Timing</span>
            <div className="seg full" role="group" aria-label="Adaptive timing">
              {(["timed", "untimed"] as const).map((value) => (
                <button key={value} type="button" className={timingMode === value ? "active" : undefined} onClick={() => setTimingMode(value)}>
                  {value === "timed" ? "Strict" : "Untimed"}
                </button>
              ))}
            </div>
          </div>
          <div className="summary-field">
            <span className="summary-field-label">Feedback</span>
            <div className="seg full" role="group" aria-label="Adaptive feedback">
              {(["strict", "guided"] as const).map((value) => (
                <button key={value} type="button" className={evaluatorFeedbackMode === value ? "active" : undefined} onClick={() => setEvaluatorFeedbackMode(value)}>
                  {value}
                </button>
              ))}
            </div>
          </div>
          <button className="command-button primary" type="submit" disabled={!canGenerate}>
            {busy ? <><Loader2 size={15} className="spin" aria-hidden="true" /> Working…</> : <><Brain size={16} aria-hidden="true" /> Generate adaptive blueprint</>}
          </button>
          <p className="hint">This creates a saved draft plan. It does not send an invite until you approve it.</p>
          {error ? <p className="submission-error">{error}</p> : null}
        </div>
      </form>

      {savedBlueprints.length ? (
        <div className="assessment-section" style={{ marginTop: 16 }}>
          <div className="assessment-section-header">Saved blueprints</div>
          <p className="assessment-section-note">Showing the latest five. Blue = draft, green = invite sent, amber = future module.</p>
          <div className="activity-list">
            {savedBlueprints.slice(0, 5).map((item) => {
              const meta = blueprintStatusMeta(item, blueprint?.id === item.id);
              return (
                <button
                  className={`activity-row blueprint-row${blueprint?.id === item.id ? " active" : ""}`}
                  key={item.id}
                  type="button"
                  onClick={() => setBlueprint(item)}
                  style={{ width: "100%", textAlign: "left" }}
                >
                  <span className="activity-dot" style={{ background: meta.dot }} />
                  <span className="activity-text">
                    <strong>{item.title}</strong> — {item.assessment_level} · {item.duration_minutes} min
                  </span>
                  <span className={`status-pill ${meta.pillClass}`}>{meta.label}</span>
                  <span className="activity-time">{timeAgo(item.created_at)}</span>
                  <span className="status-pill">{meta.action}</span>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      {adaptiveInviteUrl ? (
        <div className="invite-result" style={{ marginTop: 16 }}>
          <div className="assessment-section-header">Invite created from adaptive blueprint</div>
          <input
            className="invite-url-input"
            readOnly
            value={adaptiveInviteUrl}
            aria-label="Adaptive invite URL"
            onFocus={(event) => event.currentTarget.select()}
          />
          <div className="invite-result-actions">
            <button type="button" className="command-button secondary" onClick={copyAdaptiveInviteUrl}>
              <ClipboardCopy size={16} aria-hidden="true" />
              Copy link
            </button>
            <a className="command-button secondary" href={adaptiveInviteUrl} target="_blank" rel="noreferrer">
              <ExternalLink size={16} aria-hidden="true" />
              Open assessment
            </a>
          </div>
        </div>
      ) : null}

      {blueprint ? (
        <div className="icard show" style={{ display: "block", marginTop: 16 }}>
          <div className="ihead">
            <div className="ilogo">{isFutureBlueprint ? "F" : blueprint.assessment_level === "advanced" ? "A" : "S"}</div>
            <div>
              <div className="iname">{blueprint.title}</div>
              <div className="iurl">{blueprint.coverage.label} · {blueprint.duration_minutes} min</div>
            </div>
          </div>
          <div className="ibody">
            <div className="assessment-section">
              <div className="assessment-section-header">What happens next</div>
              <p className="assessment-section-note">
                {isFutureBlueprint
                  ? "This blueprint maps the JD/resume to a planned assessment module. It is saved for review, but cannot create a candidate invite until that module is available."
                  : `This blueprint recommends the ${blueprint.assessment_level === "advanced" ? "Advanced FastAPI" : "Standard FastAPI"} coding challenge. The candidate sees the normal coding workspace after you approve and send the invite.`}
              </p>
              {isFutureBlueprint ? (
                <span className="status-pill warn">Planned assessment</span>
              ) : (
                <button
                  className="command-button secondary"
                  type="button"
                  onClick={() => setShowBlueprintAssessmentDetail(blueprint.assessment_level as "standard" | "advanced")}
                >
                  <Info size={16} aria-hidden="true" /> View assessment details
                </button>
              )}
            </div>
            <SkillPills title="Directly tested" skills={blueprint.coverage.directly_tested} tone="ready" />
            <SkillPills title="Partially tested" skills={blueprint.coverage.partially_tested} />
            <SkillPills
              title="Not directly tested"
              skills={uniqueSkills([
                ...(blueprint.skill_mapping.unsupported_required ?? []),
                ...(blueprint.skill_mapping.unsupported_claimed ?? []),
              ])}
              tone="warn"
            />
            <div className="assessment-section">
              <div className="assessment-section-header">Rationale</div>
              <ul className="assessment-list">
                {blueprint.rationale.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
            <div className="assessment-section">
              <div className="assessment-section-header">Follow-up probes</div>
              <ul className="assessment-list">
                {blueprint.follow_up_probes.slice(0, 4).map((probe) => <li key={`${probe.source}-${probe.skill_id}`}>{probe.question}</li>)}
              </ul>
            </div>
            <button className="command-button primary" type="button" disabled={!canInvite} onClick={approveAndSend}>
              {busy ? <><Loader2 size={15} className="spin" aria-hidden="true" /> Sending…</> : <><Plus size={16} aria-hidden="true" /> Approve and send invite</>}
            </button>
            {isFutureBlueprint ? <p className="hint">Invite sending is disabled because this assessment is planned for a future module.</p> : null}
            {blueprint.status === "used" ? <p className="hint">This blueprint already created an invite. Generate a new blueprint or select another saved draft to send a new invite.</p> : null}
            {!emailValid ? <p className="hint">Enter a valid candidate email before sending.</p> : null}
          </div>
        </div>
      ) : null}
      {showBlueprintAssessmentDetail ? (
        <AssessmentDetailModal
          level={showBlueprintAssessmentDetail}
          onClose={() => setShowBlueprintAssessmentDetail(null)}
        />
      ) : null}
    </section>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

function EmployerDashboard({ getAuthToken, isClerkLoaded }: { getAuthToken: AuthTokenProvider; isClerkLoaded: boolean }) {
  const [attempts, setAttempts] = useState<EmployerAttemptSummary[]>([]);
  const [creationMode, setCreationMode] = useState<"direct" | "adaptive">("direct");
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
  const [nav, setNav] = useState<"Overview" | "Assessments" | "Candidates" | "Reports">("Overview");
  const [filter, setFilter] = useState<"All" | "Submitted" | "In progress" | "Invited">("All");

  const emailValid = useMemo(() => {
    const trimmed = candidateEmail.trim();
    return trimmed.length > 0 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed);
  }, [candidateEmail]);

  const recommendedMinutes = assessmentLevel === "advanced" ? 120 : 90;
  const totalTime = timingMode === "timed" ? durationMinutes : recommendedMinutes;

  const submittedCount = useMemo(
    () => attempts.filter((attempt) => attempt.status === "submitted").length,
    [attempts],
  );
  const reportCount = useMemo(
    () => attempts.filter((attempt) => attempt.report_id !== null).length,
    [attempts],
  );

  const isInProgress = (status: string) =>
    status === "opened" || status === "in_progress" || status === "started";

  const inProgressCount = useMemo(
    () => attempts.filter((attempt) => isInProgress(attempt.status)).length,
    [attempts],
  );
  const invitedCount = useMemo(
    () => attempts.filter((attempt) => attempt.status === "created").length,
    [attempts],
  );

  function statusInfo(status: string): { label: string; cls: string; dot: string } {
    if (status === "submitted") return { label: "Submitted", cls: "ready", dot: "var(--green)" };
    if (status === "expired") return { label: "Expired", cls: "error", dot: "var(--red)" };
    if (isInProgress(status)) return { label: "In progress", cls: "info", dot: "var(--blue)" };
    if (status === "created") return { label: "Invited", cls: "warn", dot: "var(--amber)" };
    return { label: status, cls: "warn", dot: "var(--t2)" };
  }

  const filteredAttempts = useMemo(() => {
    if (filter === "All") return attempts;
    if (filter === "Submitted") return attempts.filter((a) => a.status === "submitted");
    if (filter === "Invited") return attempts.filter((a) => a.status === "created");
    return attempts.filter((a) => isInProgress(a.status));
  }, [attempts, filter]);

  const reportAttempts = useMemo(
    () => attempts.filter((a) => a.status === "submitted"),
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
    const initialLoad = window.setTimeout(() => void refreshAttempts(), 0);
    const interval = window.setInterval(() => void refreshAttempts(), 30_000);
    return () => {
      window.clearTimeout(initialLoad);
      window.clearInterval(interval);
    };
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

  const navItems = [
    { key: "Overview", icon: LayoutDashboard },
    { key: "Assessments", icon: ClipboardList },
    { key: "Candidates", icon: Users },
    { key: "Reports", icon: BarChart3 },
  ] as const;

  const tableHead = (
    <div className="attempt-row table-head">
      <span>Candidate</span>
      <span>Status</span>
      <span>Configuration</span>
      <span>Score</span>
      <span>Action</span>
    </div>
  );

  const attemptRow = (attempt: EmployerAttemptSummary) => {
    const s = statusInfo(attempt.status);
    return (
      <div className="attempt-row" key={attempt.attempt_id}>
        <div className="attempt-email-meta">
          <span>{attempt.candidate_email ?? "No email"}</span>
          <span className="attempt-sent-at">{timeAgo(attempt.created_at)}</span>
        </div>
        <span>
          <span className={`status-pill ${s.cls}`}>{s.label}</span>
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
        <span className="attempt-actions">
          <a
            className="command-button secondary"
            href={attempt.invite_url}
            target="_blank"
            rel="noreferrer"
            title="Open the candidate's assessment link"
          >
            <ExternalLink size={15} aria-hidden="true" />
            Assessment
          </a>
          {attempt.status === "submitted" ? (
            <Link className="command-button secondary" href={`/employer/reports/${attempt.attempt_id}`}>
              <FileText size={16} aria-hidden="true" />
              {attempt.report_id ? "View report" : "Generate"}
            </Link>
          ) : null}
        </span>
      </div>
    );
  };

  return (
    <div className="portal-shell">
      <header className="portal-topbar">
        <div className="portal-topbar-brand">
          <Logo />
          <div>
            <h1>SignalLoop</h1>
            <p>Employer workspace</p>
          </div>
        </div>
        <UserButton />
      </header>
      <div className="portal-body">
        <nav className="portal-sidebar">
          <div className="portal-nav-label">Workspace</div>
          {navItems.map(({ key, icon: Icon }) => (
            <button
              key={key}
              type="button"
              className={`portal-nav-item${nav === key ? " active" : ""}`}
              onClick={() => setNav(key)}
            >
              <Icon size={16} aria-hidden="true" />
              {key}
            </button>
          ))}
          <div className="portal-nav-spacer" />
          <div className="portal-nav-label">Account</div>
          <button type="button" className="portal-nav-item" title="Coming soon">
            <Settings size={16} aria-hidden="true" />
            Settings
          </button>
          <button type="button" className="portal-nav-item" title="Coming soon">
            <BookOpen size={16} aria-hidden="true" />
            Help &amp; docs
          </button>
        </nav>
        <main className="portal-content">
          <div className="portal-content-inner">

            {nav === "Overview" ? (
              <>
                <div className="view-head">
                  <h2>Overview</h2>
                  <p>Workspace activity at a glance.</p>
                </div>
                <section className="metric-row" style={{ marginBottom: 24 }}>
                  <div className="metric"><span>Total candidates</span><strong style={{ color: "var(--blue)" }}>{attempts.length}</strong></div>
                  <div className="metric"><span>Submitted</span><strong style={{ color: "var(--green)" }}>{submittedCount}</strong></div>
                  <div className="metric"><span>In progress</span><strong style={{ color: "var(--amber)" }}>{inProgressCount}</strong></div>
                  <div className="metric"><span>Invited</span><strong style={{ color: "var(--purple)" }}>{invitedCount}</strong></div>
                </section>
                <CreationPathsOverview />
                <HowItWorks />
                <div className="section-title" style={{ margin: "24px 0 12px" }}>
                  <h2 style={{ fontSize: 15, display: "flex", alignItems: "center", gap: 8 }}>
                    <Activity size={16} aria-hidden="true" /> Recent activity
                  </h2>
                </div>
                {attempts.length ? (
                  <div className="activity-list">
                    {attempts.slice(0, 8).map((a) => {
                      const s = statusInfo(a.status);
                      return (
                        <div className="activity-row" key={a.attempt_id}>
                          <span className="activity-dot" style={{ background: s.dot }} />
                          <span className="activity-text"><strong>{a.candidate_email ?? "Candidate"}</strong> — {s.label.toLowerCase()}</span>
                          <span className="activity-time">{timeAgo(a.created_at)}</span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="empty-state">No activity yet — use Direct coding challenge or Adaptive builder on the Assessments page.</p>
                )}
              </>
            ) : null}

            {nav === "Assessments" ? (
              <>
                <div className="view-head">
                  <h2>Build assessment</h2>
                  <p>Choose one creation path. Direct uses your manual coding challenge selection; Adaptive generates the selection from a JD/resume blueprint.</p>
                </div>

                <div className="summary-field" style={{ marginBottom: 18 }}>
                  <span className="summary-field-label">Creation path</span>
                  <div className="seg full" role="group" aria-label="Assessment creation path">
                    <button
                      type="button"
                      className={creationMode === "direct" ? "active" : undefined}
                      onClick={() => setCreationMode("direct")}
                    >
                      Direct coding challenge
                    </button>
                    <button
                      type="button"
                      className={creationMode === "adaptive" ? "active" : undefined}
                      onClick={() => setCreationMode("adaptive")}
                    >
                      Adaptive builder
                    </button>
                  </div>
                  <p className="hint">
                    {creationMode === "adaptive"
                      ? "Adaptive mode hides the manual coding form. The approved blueprint decides Basic vs Advanced and sends the invite."
                      : "Direct mode skips blueprint generation. You manually choose Basic or Advanced and send the invite."}
                  </p>
                </div>

                {creationMode === "adaptive" ? (
                  <AdaptiveBuilder
                    getAuthToken={getAuthToken}
                    onCreated={(updatedAttempts, inviteUrl) => {
                      setAttempts(updatedAttempts);
                      setCreatedInviteUrl(inviteUrl);
                    }}
                  />
                ) : null}

                {creationMode === "direct" ? (
        <form className="build-grid" onSubmit={submitInvite}>
          <div className="build-left">
          {/* Left: the single supported module — Python coding challenge */}
          <div className="mod-card">
            <div className="mod-card-head">
              <span className="mod-icon">
                <Code2 size={18} aria-hidden="true" />
              </span>
              <div>
                <p className="mod-title">Coding challenge</p>
                <p className="mod-sub">Python · debug &amp; extend a FastAPI service</p>
              </div>
            </div>
            <div className="mod-tags">
              <span className="mod-tag">Debugging</span>
              <span className="mod-tag">API design</span>
              <span className="mod-tag">Pytest</span>
            </div>
            <p className="mod-desc">{ASSESSMENT_INFO[assessmentLevel].description}</p>
            <div className="mod-divider" />
            <div>
              <div className="mod-row">
                <span className="mod-row-label">
                  <Code2 size={13} aria-hidden="true" /> Language
                </span>
                <span className="mod-time">Python</span>
              </div>
              <div className="mod-row">
                <span className="mod-row-label">
                  <Info size={13} aria-hidden="true" /> Level
                </span>
                <div className="seg" role="group" aria-label="Assessment level">
                  {([
                    ["standard", "Basic"],
                    ["advanced", "Advanced"],
                  ] as const).map(([value, label]) => (
                    <button
                      key={value}
                      type="button"
                      className={assessmentLevel === value ? "active" : undefined}
                      onClick={() => {
                        setAssessmentLevel(value);
                        setDurationMinutes(value === "advanced" ? 120 : 90);
                      }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="mod-row">
                <span className="mod-row-label">
                  <Clock size={13} aria-hidden="true" /> Recommended time
                </span>
                <span className="mod-time">{recommendedMinutes}m</span>
              </div>
            </div>
            <button
              type="button"
              className="text-button"
              onClick={() => setShowAssessmentDetail(true)}
            >
              <Info size={14} aria-hidden="true" />
              Assessment details
            </button>
          </div>

          <div className="roadmap-label">More assessment types — coming soon</div>
          <div className="module-grid">
            {COMING_SOON_MODULES.map((m) => {
              const Icon = m.icon;
              return (
                <div className="mod-card soon" key={m.name} aria-disabled="true">
                  <div className="mod-card-head">
                    <span
                      className="mod-card-soonicon"
                      style={{ background: m.bg, color: m.color, borderColor: m.color }}
                    >
                      <Icon size={18} aria-hidden="true" />
                    </span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p className="mod-title">{m.name}</p>
                    </div>
                    <span className="mod-soon-badge">Coming soon</span>
                  </div>
                  <div className="mod-tags">
                    {m.tags.map((t) => <span className="mod-tag" key={t}>{t}</span>)}
                  </div>
                  <p className="mod-desc">{m.desc}</p>
                </div>
              );
            })}
          </div>
          </div>

          {/* Right: assessment summary + send invite (Calibr context panel) */}
          <div className="build-summary">
            <div>
              <h3>Assessment summary</h3>
              <p className="build-summary-sub">Active configuration</p>
            </div>
            <div className="summary-tiles">
              <div className="summary-tile">
                <div className="summary-tile-label">Modules</div>
                <div className="summary-tile-value">1</div>
                <div className="summary-tile-unit">selected</div>
              </div>
              <div className="summary-tile">
                <div className="summary-tile-label">Total time</div>
                <div className="summary-tile-value">{totalTime}</div>
                <div className="summary-tile-unit">minutes</div>
              </div>
            </div>

            <div className="build-divider" />

            <div className="summary-field">
              <span className="summary-field-label">Candidate email</span>
              <input
                id="candidate-email"
                type="email"
                required
                value={candidateEmail}
                onChange={(event) => setCandidateEmail(event.target.value)}
                placeholder="candidate@company.com"
                className="text-input"
                aria-label="Candidate email"
                aria-describedby={candidateEmail && !emailValid ? "email-error" : undefined}
              />
              {candidateEmail && !emailValid ? (
                <span id="email-error" className="submission-error" style={{ marginTop: 0 }}>
                  Enter a valid email address
                </span>
              ) : null}
            </div>

            <div className="summary-field">
              <span className="summary-field-label">Timing enforcement</span>
              <div className="seg full" role="group" aria-label="Timing enforcement">
                {([
                  ["timed", "Strict"],
                  ["untimed", "Untimed"],
                ] as const).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    className={timingMode === value ? "active" : undefined}
                    onClick={() => {
                      setTimingMode(value);
                      if (value === "timed") setDurationMinutes(recommendedMinutes);
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {timingMode === "timed" ? (
              <div className="summary-field">
                <span className="summary-field-label">Duration</span>
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
              </div>
            ) : null}

            <div className="summary-field">
              <span className="summary-field-label">Evaluator feedback</span>
              <div className="seg full" role="group" aria-label="Evaluator feedback">
                {([
                  ["strict", "Strict"],
                  ["guided", "Guided"],
                ] as const).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    className={evaluatorFeedbackMode === value ? "active" : undefined}
                    onClick={() => setEvaluatorFeedbackMode(value)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <button className="command-button primary" disabled={creating || !emailValid} type="submit">
              {creating
                ? <><Loader2 size={15} className="spin" aria-hidden="true" /> Creating…</>
                : <><Plus size={17} aria-hidden="true" /> Send invite</>
              }
            </button>

            {error ? <p className="submission-error" style={{ marginTop: 0 }}>{error}</p> : null}

            {createdInviteUrl ? (
              <div className="invite-result">
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
          </div>
        </form>
                ) : null}
              </>
            ) : null}

            {nav === "Candidates" ? (
              <>
                <div className="view-head">
                  <h2>Candidates</h2>
                  <p>All candidate attempts, scores, and status.</p>
                </div>
                <div className="filter-bar">
                  {(["All", "Submitted", "In progress", "Invited"] as const).map((f) => (
                    <button
                      key={f}
                      type="button"
                      className={`filter-pill${filter === f ? " active" : ""}`}
                      onClick={() => setFilter(f)}
                    >
                      {f}
                    </button>
                  ))}
                  <span className="filter-count">
                    {filteredAttempts.length} {filteredAttempts.length === 1 ? "candidate" : "candidates"}
                    {loading ? " · refreshing…" : ""}
                  </span>
                </div>
                <div className="attempt-table">
                  {tableHead}
                  {filteredAttempts.map((a) => attemptRow(a))}
                  {!filteredAttempts.length && !loading ? (
                    <p className="empty-state">No candidates in this view.</p>
                  ) : null}
                </div>
              </>
            ) : null}

            {nav === "Reports" ? (
              <>
                <div className="view-head">
                  <h2>Reports</h2>
                  <p>Submitted attempts and generated evidence reports.</p>
                </div>
                <div className="attempt-table">
                  {tableHead}
                  {reportAttempts.map((a) => attemptRow(a))}
                  {!reportAttempts.length ? (
                    <p className="empty-state">No submitted attempts yet.</p>
                  ) : null}
                </div>
              </>
            ) : null}

          </div>
        </main>
      </div>

      {showAssessmentDetail ? (
        <AssessmentDetailModal
          level={assessmentLevel}
          onClose={() => setShowAssessmentDetail(false)}
        />
      ) : null}
    </div>
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
