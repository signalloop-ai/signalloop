import type { EmployerAttemptSummary, EvidenceReportResponse } from "./types";

export const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function fetchAttempts(): Promise<EmployerAttemptSummary[]> {
  const response = await fetch(`${apiBaseUrl}/assessment-attempts`);
  if (!response.ok) {
    throw new ApiError(`Attempt list failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as EmployerAttemptSummary[];
}

export async function createInvite(candidateEmail: string): Promise<EmployerAttemptSummary[]> {
  const response = await fetch(`${apiBaseUrl}/assessment-attempts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ candidate_email: candidateEmail || null }),
  });
  if (!response.ok) {
    throw new ApiError(`Invite creation failed with HTTP ${response.status}`, response.status);
  }
  return fetchAttempts();
}

export async function fetchReport(attemptId: string): Promise<EvidenceReportResponse> {
  const response = await fetch(`${apiBaseUrl}/assessment-attempts/${attemptId}/evidence-report`);
  if (!response.ok) {
    throw new ApiError(`Report load failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as EvidenceReportResponse;
}

export async function generateReport(attemptId: string): Promise<EvidenceReportResponse> {
  const response = await fetch(`${apiBaseUrl}/assessment-attempts/${attemptId}/evidence-report`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new ApiError(`Report generation failed with HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as EvidenceReportResponse;
}
