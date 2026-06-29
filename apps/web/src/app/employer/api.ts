import type { AssessmentBlueprint, EmployerAttemptSummary, EvidenceReportResponse } from "./types";

export const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
export type AuthTokenProvider = () => Promise<string | null>;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function employerHeaders(getAuthToken?: AuthTokenProvider): Promise<HeadersInit> {
  const headers: Record<string, string> = {};
  const token = getAuthToken ? await getAuthToken() : null;
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

export async function fetchAttempts(getAuthToken?: AuthTokenProvider): Promise<EmployerAttemptSummary[]> {
  const response = await fetch(`${apiBaseUrl}/assessment-attempts`, {
    headers: await employerHeaders(getAuthToken),
  });
  if (!response.ok) {
    throw new ApiError(`Attempt list failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as EmployerAttemptSummary[];
}

export type InviteConfiguration = {
  assessmentLevel: "standard" | "advanced";
  timingMode: "untimed" | "timed";
  evaluatorFeedbackMode: "strict" | "guided";
  durationMinutes: number;
};

export async function createInvite(
  candidateEmail: string,
  configuration: InviteConfiguration,
  getAuthToken?: AuthTokenProvider,
): Promise<EmployerAttemptSummary[]> {
  const response = await fetch(`${apiBaseUrl}/assessment-attempts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(await employerHeaders(getAuthToken)),
    },
    body: JSON.stringify({
      candidate_email: candidateEmail || null,
      assessment_level: configuration.assessmentLevel,
      timing_mode: configuration.timingMode,
      evaluator_feedback_mode: configuration.evaluatorFeedbackMode,
      duration_minutes: configuration.durationMinutes,
    }),
  });
  if (!response.ok) {
    let detail = `Invite creation failed with HTTP ${response.status}`;
    try {
      const body = await response.json() as { detail?: string; errors?: Array<{ msg: string }> };
      if (body.errors?.[0]?.msg) {
        detail = body.errors[0].msg;
      } else if (typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // keep the generic message if body can't be parsed
    }
    throw new ApiError(detail, response.status);
  }
  return fetchAttempts(getAuthToken);
}

export type AdaptiveBuilderInput = {
  roleTitle: string;
  roleFamily: "backend" | "frontend" | "fullstack" | "infra" | "data" | "ai" | "security" | "support";
  seniority: "junior" | "mid" | "senior" | "staff";
  jdText: string;
  teamContext: string;
  expectedAiUsage: number;
  candidateEmail: string;
  resumeText: string;
  timingMode: "untimed" | "timed";
  evaluatorFeedbackMode: "strict" | "guided";
};

async function parseApiError(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json() as { detail?: string; errors?: Array<{ msg: string }> };
    if (body.errors?.[0]?.msg) return body.errors[0].msg;
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // keep fallback
  }
  return fallback;
}

async function authedJson<T>(
  path: string,
  body: unknown,
  getAuthToken?: AuthTokenProvider,
): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(await employerHeaders(getAuthToken)),
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new ApiError(await parseApiError(response, `${path} failed with HTTP ${response.status}`), response.status);
  }
  return (await response.json()) as T;
}

export async function generateAdaptiveBlueprint(
  input: AdaptiveBuilderInput,
  getAuthToken?: AuthTokenProvider,
): Promise<AssessmentBlueprint> {
  const role = await authedJson<{ id: number }>("/employer/adaptive/role-profiles", {
    title: input.roleTitle,
    role_family: input.roleFamily,
    seniority: input.seniority,
    jd_text: input.jdText,
    team_context: input.teamContext || null,
    expected_ai_usage: input.expectedAiUsage,
  }, getAuthToken);

  let candidateProfileId: number | null = null;
  if (input.resumeText.trim()) {
    const candidate = await authedJson<{ id: number }>("/employer/adaptive/candidate-profiles", {
      candidate_email: input.candidateEmail || null,
      resume_text: input.resumeText,
    }, getAuthToken);
    candidateProfileId = candidate.id;
  }

  return authedJson<AssessmentBlueprint>("/employer/adaptive/blueprints", {
    role_profile_id: role.id,
    candidate_profile_id: candidateProfileId,
    timing_mode: input.timingMode,
    evaluator_feedback_mode: input.evaluatorFeedbackMode,
  }, getAuthToken);
}

export async function fetchAdaptiveBlueprints(getAuthToken?: AuthTokenProvider): Promise<AssessmentBlueprint[]> {
  const response = await fetch(`${apiBaseUrl}/employer/adaptive/blueprints`, {
    headers: await employerHeaders(getAuthToken),
  });
  if (!response.ok) {
    throw new ApiError(await parseApiError(response, `Blueprint list failed with HTTP ${response.status}`), response.status);
  }
  return (await response.json()) as AssessmentBlueprint[];
}

export async function extractDocumentText(file: File, getAuthToken?: AuthTokenProvider): Promise<{ filename: string; text: string }> {
  const response = await fetch(`${apiBaseUrl}/employer/adaptive/extract-document-text`, {
    method: "POST",
    headers: {
      "Content-Type": "application/octet-stream",
      "X-Filename": file.name,
      ...(await employerHeaders(getAuthToken)),
    },
    body: await file.arrayBuffer(),
  });
  if (!response.ok) {
    throw new ApiError(await parseApiError(response, `Document upload failed with HTTP ${response.status}`), response.status);
  }
  return (await response.json()) as { filename: string; text: string };
}

export async function approveAndInviteFromBlueprint(
  blueprintId: number,
  candidateEmail: string,
  getAuthToken?: AuthTokenProvider,
): Promise<{ attempts: EmployerAttemptSummary[]; inviteUrl: string | null }> {
  await authedJson<AssessmentBlueprint>(`/employer/adaptive/blueprints/${blueprintId}/approve`, {}, getAuthToken);
  const created = await authedJson<{ invite_url: string }>(
    `/employer/adaptive/blueprints/${blueprintId}/invites`,
    { candidate_email: candidateEmail || null },
    getAuthToken,
  );
  return {
    attempts: await fetchAttempts(getAuthToken),
    inviteUrl: created.invite_url,
  };
}

export async function fetchReport(attemptId: string, getAuthToken?: AuthTokenProvider): Promise<EvidenceReportResponse> {
  const response = await fetch(`${apiBaseUrl}/assessment-attempts/${attemptId}/evidence-report`, {
    headers: await employerHeaders(getAuthToken),
  });
  if (!response.ok) {
    throw new ApiError(`Report load failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as EvidenceReportResponse;
}

export async function generateReport(attemptId: string, getAuthToken?: AuthTokenProvider): Promise<EvidenceReportResponse> {
  const response = await fetch(`${apiBaseUrl}/assessment-attempts/${attemptId}/evidence-report`, {
    method: "POST",
    headers: await employerHeaders(getAuthToken),
  });
  if (!response.ok) {
    throw new ApiError(`Report generation failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as EvidenceReportResponse;
}
