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
    failed_test_runs: number;
    error_attempts: number;
    missing_reports: number;
  };
  attempts: AdminAttemptSummary[];
};

export type AdminEvidenceReport = {
  attempt_id: number;
  report_id: number;
  recommendation: string | null;
  score_total: number | null;
  report: Record<string, unknown>;
};