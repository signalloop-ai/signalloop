export type EmployerInfo = {
  id: number;
  email: string;
  role: string | null;
};

export type AdminEmployerSummary = {
  id: number;
  email: string;
  company_name: string | null;
  role: string | null;
  created_at: string;
  last_activity_at: string | null;
  invite_count: number;
  attempt_count: number;
  submitted_count: number;
  report_count: number;
  avg_score: number | null;
};

export type AdminAttemptSummary = {
  id: number;
  candidate_email: string | null;
  assessment_pack_slug: string | null;
  status: string;
  created_at: string;
  submitted_at: string | null;
  score_total: number | null;
  recommendation: string | null;
  report_id: number | null;
};

export type AdminEmployerDetail = {
  id: number;
  email: string;
  company_name: string | null;
  role: string | null;
  created_at: string;
  invite_count: number;
  attempt_count: number;
  submitted_count: number;
  report_count: number;
  status_breakdown: Record<string, number>;
  score_distribution: {
    average: number | null;
    median: number | null;
    min: number | null;
    max: number | null;
  };
  ai_usage: {
    total_messages: number;
    total_violations: number;
  };
  pack_breakdown: Record<string, number>;
  stuck_signals: {
    execution_errors: number;
    missing_reports: number;
  };
  attempts: AdminAttemptSummary[];
};

export type QuestionSource = {
  id: number;
  source_id: string;
  name: string;
  url: string;
  license: string;
  recommended_use: string;
  attribution_required: boolean;
  notes: string | null;
  status: string;
  created_at: string;
};

export type QuestionBankQuestion = {
  id: number;
  source: QuestionSource | null;
  version: number;
  status: string;
  title: string;
  question_type: string;
  prompt: string;
  role_tags: string[];
  skill_tags: string[];
  cognitive_tags: string[];
  difficulty: "easy" | "medium" | "hard" | string;
  seniority: string;
  estimated_minutes: number;
  rubric: { dimensions?: string[]; scale?: string; [key: string]: unknown };
  expected_evidence: string[];
  provenance: Record<string, unknown>;
  generated_by: string;
  package_status: string;
  coding_package_kind: string | null;
  coding_package_ref: string | null;
  coding_package_notes: string | null;
  assessment_ready: boolean;
  reviewed_by_id: number | null;
  reviewed_at: string | null;
  review_notes: string | null;
  created_at: string;
};

export type QuestionBankSeedResult = {
  source_count: number;
  question_count: number;
  created_sources: number;
  created_questions: number;
};

export type QuestionBankImportResult = {
  fetched_sources: number;
  created_questions: number;
  errors: Array<Record<string, unknown>>;
  question_count: number;
};

export type QuestionBankQuestionUpdate = Partial<Pick<
  QuestionBankQuestion,
  | "title"
  | "question_type"
  | "prompt"
  | "role_tags"
  | "skill_tags"
  | "cognitive_tags"
  | "difficulty"
  | "seniority"
  | "estimated_minutes"
  | "rubric"
  | "expected_evidence"
  | "package_status"
  | "coding_package_kind"
  | "coding_package_ref"
  | "coding_package_notes"
  | "review_notes"
>>;

// The admin report endpoint returns the same shape as the employer one, so reuse the typed
// response — the shared EvidenceReportView renders both.
export type { EvidenceReportResponse as AdminEvidenceReport } from "../employer/types";
