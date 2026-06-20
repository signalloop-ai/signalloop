import type { EmployerAttemptSummary, EvidenceReportResponse } from "./types";

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
