import type { AdminEmployerDetail, AdminEmployerSummary, AdminEvidenceReport, EmployerInfo } from "./types";
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