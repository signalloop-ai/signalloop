import type {
  AdminEmployerDetail,
  AdminEmployerSummary,
  AdminEvidenceReport,
  EmployerInfo,
  QuestionBankQuestion,
  QuestionBankQuestionUpdate,
  QuestionBankImportResult,
  QuestionBankSeedResult,
  QuestionSource,
} from "./types";
import { ApiError, apiBaseUrl } from "../employer/api";

// Single source of truth for the API base URL — re-exported from the employer client so the
// two portals can never drift to different defaults.
export { apiBaseUrl };
export type AuthTokenProvider = () => Promise<string | null>;

async function adminHeaders(getAuthToken?: AuthTokenProvider): Promise<HeadersInit> {
  const headers: Record<string, string> = {};
  const token = getAuthToken ? await getAuthToken() : null;
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

export async function fetchAdminMe(getAuthToken?: AuthTokenProvider): Promise<EmployerInfo> {
  const response = await fetch(`${apiBaseUrl}/admin/me`, {
    headers: await adminHeaders(getAuthToken),
  });
  if (!response.ok) {
    throw new ApiError(`Admin auth check failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as EmployerInfo;
}

export async function fetchEmployerMe(getAuthToken?: AuthTokenProvider): Promise<EmployerInfo> {
  const response = await fetch(`${apiBaseUrl}/employer/me`, {
    headers: await adminHeaders(getAuthToken),
  });
  if (!response.ok) {
    throw new ApiError(`Employer auth check failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as EmployerInfo;
}

export async function fetchAdminEmployers(getAuthToken?: AuthTokenProvider): Promise<AdminEmployerSummary[]> {
  const response = await fetch(`${apiBaseUrl}/admin/employers`, {
    headers: await adminHeaders(getAuthToken),
  });
  if (!response.ok) {
    throw new ApiError(`Employer list failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as AdminEmployerSummary[];
}

export async function fetchAdminEmployerDetail(
  employerId: string,
  getAuthToken?: AuthTokenProvider,
): Promise<AdminEmployerDetail> {
  const response = await fetch(`${apiBaseUrl}/admin/employers/${employerId}`, {
    headers: await adminHeaders(getAuthToken),
  });
  if (!response.ok) {
    throw new ApiError(`Employer detail failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as AdminEmployerDetail;
}

export async function fetchAdminReport(
  attemptId: string,
  getAuthToken?: AuthTokenProvider,
): Promise<AdminEvidenceReport> {
  const response = await fetch(`${apiBaseUrl}/admin/attempts/${attemptId}/report`, {
    headers: await adminHeaders(getAuthToken),
  });
  if (!response.ok) {
    throw new ApiError(`Admin report load failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as AdminEvidenceReport;
}

export async function seedQuestionBankDrafts(getAuthToken?: AuthTokenProvider): Promise<QuestionBankSeedResult> {
  const response = await fetch(`${apiBaseUrl}/admin/question-bank/seed-drafts`, {
    method: "POST",
    headers: await adminHeaders(getAuthToken),
  });
  if (!response.ok) {
    throw new ApiError(`Question bank seed failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as QuestionBankSeedResult;
}

export async function importSourceQuestions(getAuthToken?: AuthTokenProvider): Promise<QuestionBankImportResult> {
  const response = await fetch(`${apiBaseUrl}/admin/question-bank/import-source-questions`, {
    method: "POST",
    headers: await adminHeaders(getAuthToken),
  });
  if (!response.ok) {
    throw new ApiError(`Question import failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as QuestionBankImportResult;
}

export async function fetchQuestionSources(getAuthToken?: AuthTokenProvider): Promise<QuestionSource[]> {
  const response = await fetch(`${apiBaseUrl}/admin/question-bank/sources`, {
    headers: await adminHeaders(getAuthToken),
  });
  if (!response.ok) {
    throw new ApiError(`Question source list failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as QuestionSource[];
}

export async function fetchQuestionBankQuestions(
  statusFilter?: string,
  getAuthToken?: AuthTokenProvider,
): Promise<QuestionBankQuestion[]> {
  const params = statusFilter && statusFilter !== "all" ? `?status_filter=${encodeURIComponent(statusFilter)}` : "";
  const response = await fetch(`${apiBaseUrl}/admin/question-bank/questions${params}`, {
    headers: await adminHeaders(getAuthToken),
  });
  if (!response.ok) {
    throw new ApiError(`Question list failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as QuestionBankQuestion[];
}

export async function updateQuestionBankQuestion(
  questionId: number,
  payload: QuestionBankQuestionUpdate,
  getAuthToken?: AuthTokenProvider,
): Promise<QuestionBankQuestion> {
  const response = await fetch(`${apiBaseUrl}/admin/question-bank/questions/${questionId}`, {
    method: "PATCH",
    headers: { ...(await adminHeaders(getAuthToken)), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new ApiError(`Question update failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as QuestionBankQuestion;
}

export async function reviewQuestionBankQuestion(
  questionId: number,
  action: "approve" | "reject",
  reviewNotes: string,
  getAuthToken?: AuthTokenProvider,
): Promise<QuestionBankQuestion> {
  const response = await fetch(`${apiBaseUrl}/admin/question-bank/questions/${questionId}/${action}`, {
    method: "POST",
    headers: { ...(await adminHeaders(getAuthToken)), "Content-Type": "application/json" },
    body: JSON.stringify({ review_notes: reviewNotes || null }),
  });
  if (!response.ok) {
    throw new ApiError(`Question ${action} failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as QuestionBankQuestion;
}

export async function reviewQuestionBankPackage(
  questionId: number,
  action: "approve" | "reject",
  reviewNotes: string,
  getAuthToken?: AuthTokenProvider,
): Promise<QuestionBankQuestion> {
  const response = await fetch(`${apiBaseUrl}/admin/question-bank/questions/${questionId}/package/${action}`, {
    method: "POST",
    headers: { ...(await adminHeaders(getAuthToken)), "Content-Type": "application/json" },
    body: JSON.stringify({ review_notes: reviewNotes || null }),
  });
  if (!response.ok) {
    throw new ApiError(`Coding package ${action} failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as QuestionBankQuestion;
}

export async function deleteQuestionBankQuestion(
  questionId: number,
  getAuthToken?: AuthTokenProvider,
): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/admin/question-bank/questions/${questionId}`, {
    method: "DELETE",
    headers: await adminHeaders(getAuthToken),
  });
  if (!response.ok) {
    throw new ApiError(`Question delete failed with HTTP ${response.status}`, response.status);
  }
}
