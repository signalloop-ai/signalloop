export type AssessmentMetadata = {
  slug: string;
  title: string;
  version: string;
};

export type EmployerAttemptSummary = {
  attempt_id: number;
  candidate_email: string | null;
  status: string;
  invite_token: string;
  invite_url: string;
  assessment: AssessmentMetadata;
  created_at: string;
  submitted_at: string | null;
  report_id: number | null;
  recommendation: string | null;
  score_total: number | null;
};

type TestSummary = {
  collected: number;
  passed: number;
  failed: number;
  failure_names: string[];
  status: string;
};

type PasteDetection = {
  pasted_ai_code_count: number;
  matches: Array<{ code_preview: string; found_in_files: string[] }>;
};

type LargePasteDetection = {
  large_paste_count: number;
  events: Array<{ file: string; lines_added: number; snapshot_kind: string; at: string; code_preview: string }>;
};

export type EvidenceReportResponse = {
  attempt_id: number;
  report_id: number;
  recommendation: string | null;
  score_total: number | null;
  report: {
    metadata: {
      candidate_email: string | null;
      submitted_at: string | null;
      assessment: AssessmentMetadata;
    };
    executive_summary: {
      summary: string;
      evidence_limits: string[];
    };
    overall_recommendation: string;
    scores: {
      total: number;
      max_points: number;
      confidence: string;
      categories: Array<{
        category: string;
        points: number;
        max_points: number;
        evidence: string;
      }>;
    };
    rubric_weights: Record<string, number>;
    public_test_results: {
      last_run_summary: TestSummary;
      run_count: number;
      initially_failing_tests: string[];
    };
    hidden_test_results: {
      seeded_issue_areas: string[];
      summary: TestSummary;
    };
    candidate_tests: {
      added_test_files: string[];
      modified_test_files: string[];
      candidate_test_file_count: number;
    };
    ai_collaboration: {
      message_count: number;
      candidate_prompt_count: number;
      policy_redirect_count: number;
      pasted_ai_code: PasteDetection;
      large_paste_events: LargePasteDetection;
      flagged_prompts: Array<{ message: string; policy_tags: string[]; at: string }>;
      all_candidate_messages: Array<{ message: string; at: string }>;
    };
    process_evidence: {
      snapshot_count: number;
      test_run_count: number;
      test_runs: Array<{ id: number; type: string; status: string; duration_ms: number }>;
    };
    explanation_submitted: {
      final_explanation: string;
      decision_log: string;
    };
    timeline: Array<{ at: string; type: string; summary: string }>;
    follow_up_questions: string[];
  };
};
