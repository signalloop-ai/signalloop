"use client";

import { useAuth } from "@clerk/nextjs";
import { ArrowLeft, RotateCw } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ApiError, fetchReport, generateReport } from "../../api";
import type { EvidenceReportResponse } from "../../types";
import { EvidenceReportView } from "../../../_components/EvidenceReportView";

const Logo = () => (
  <svg className="topbar-logo" width="30" height="30" viewBox="0 0 30 30" fill="none" aria-label="SignalLoop">
    <rect width="30" height="30" rx="7" fill="#3b82f6" />
    <path d="M15 6C19.97 6 24 10.03 24 15C24 19.97 19.97 24 15 24C10.5 24 6.8 20.7 6.1 16.4" stroke="white" strokeWidth="2.3" strokeLinecap="round" />
    <path d="M4.5 14.5L6.2 17.2L9 15.5" stroke="white" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="15" cy="6" r="2" fill="#22d3ee" />
  </svg>
);

export default function ReportDetail() {
  const params = useParams<{ attemptId: string | string[] }>();
  const attemptIdParam = params.attemptId;
  const attemptId = Array.isArray(attemptIdParam) ? attemptIdParam[0] : attemptIdParam;
  const { getToken, isLoaded } = useAuth();
  const [report, setReport] = useState<EvidenceReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setReport(await fetchReport(attemptId, getToken));
    } catch (loadError) {
      if (loadError instanceof ApiError && loadError.status === 404) {
        try {
          setReport(await generateReport(attemptId, getToken));
        } catch (generateError) {
          setError(generateError instanceof Error ? generateError.message : "Report generation failed");
        }
      } else {
        setError(loadError instanceof Error ? loadError.message : "Report load failed");
      }
    } finally {
      setLoading(false);
    }
  }, [attemptId, getToken]);

  useEffect(() => {
    if (!isLoaded) return;
    const timeoutId = window.setTimeout(() => void loadReport(), 0);
    return () => window.clearTimeout(timeoutId);
  }, [loadReport, isLoaded]);

  async function createReport() {
    if (!window.confirm("Regenerate will overwrite the existing AI analysis. Continue?")) return;
    setGenerating(true);
    setError(null);
    try {
      setReport(await generateReport(attemptId, getToken));
    } catch (generateError) {
      setError(generateError instanceof Error ? generateError.message : "Report generation failed");
    } finally {
      setGenerating(false);
    }
  }

  const r = report?.report;

  return (
    <main className="employer-page">
      <header className="employer-header">
        <div className="report-header-brand">
          <Logo />
          <div>
            <Link className="back-link" href="/employer">
              <ArrowLeft size={16} aria-hidden="true" />
              Back to attempts
            </Link>
            <h1>Evidence Report</h1>
            <p>
              {r?.metadata?.candidate_email ?? `Attempt #${attemptId}`}
              {r?.metadata?.assessment ? ` · ${r.metadata.assessment.title ?? r.metadata.assessment.version}` : ""}
            </p>
          </div>
        </div>
        <button className="command-button warn" disabled={generating} onClick={createReport}>
          <RotateCw size={17} aria-hidden="true" />
          {generating ? "Generating…" : "Regenerate report"}
        </button>
      </header>

      {loading ? <p className="empty-state">Loading or generating report…</p> : null}
      {error ? <p className="submission-error">{error}</p> : null}

      {report && r ? <EvidenceReportView report={report} /> : null}
    </main>
  );
}
