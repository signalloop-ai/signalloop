"use client";

import { useAuth } from "@clerk/nextjs";
import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { fetchAdminEmployerDetail } from "../../api";
import type { AdminEmployerDetail } from "../../types";

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "—";
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
  return <span className={`status-pill ${cls}`}>{score}</span>;
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default function AdminEmployerDetailPage() {
  const { getToken } = useAuth();
  const params = useParams();
  const employerId = String(params.id);
  const [detail, setDetail] = useState<AdminEmployerDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDetail(await fetchAdminEmployerDetail(employerId, getToken));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load employer");
    } finally {
      setLoading(false);
    }
  }, [employerId, getToken]);

  useEffect(() => { void refresh(); }, [refresh]);

  return (
    <main className="employer-page">
      <Link href="/admin" className="command-button secondary" style={{ display: "inline-flex", marginBottom: 16 }}>
        <ArrowLeft size={16} aria-hidden="true" /> Back to roster
      </Link>

      {error ? <p className="submission-error">{error}</p> : null}

      {loading && !detail ? (
        <p className="empty-state"><Loader2 size={16} className="spin" aria-hidden="true" /> Loading employer…</p>
      ) : null}

      {detail ? (
        <>
          <section className="employer-section">
            <div className="section-title">
              <h2>{detail.email}</h2>
              {detail.role === "super_admin" ? (
                <span className="status-pill ready" style={{ marginLeft: 8 }}>Admin</span>
              ) : null}
            </div>
            <p className="attempt-sent-at">
              Created {timeAgo(detail.created_at)}
              {detail.company_name ? ` · ${detail.company_name}` : ""}
            </p>
          </section>

          <section className="metric-row">
            <MetricCard label="Invites sent" value={detail.invite_count} />
            <MetricCard label="Submitted" value={detail.submitted_count} />
            <MetricCard label="Reports" value={detail.report_count} />
          </section>

          <section className="metric-row">
            <MetricCard label="Avg score" value={detail.score_distribution.average ?? "—"} />
            <MetricCard label="Median" value={detail.score_distribution.median ?? "—"} />
            <MetricCard label="Min" value={detail.score_distribution.min ?? "—"} />
            <MetricCard label="Max" value={detail.score_distribution.max ?? "—"} />
          </section>

          <section className="metric-row">
            <MetricCard label="AI messages" value={detail.ai_usage.total_messages} />
            <MetricCard label="AI violations" value={detail.ai_usage.total_violations} />
            <MetricCard label="Failed test runs" value={detail.stuck_signals.failed_test_runs} />
            <MetricCard label="Missing reports" value={detail.stuck_signals.missing_reports} />
          </section>

          {Object.keys(detail.status_breakdown).length > 0 ? (
            <section className="employer-section">
              <SectionTitle label="Status breakdown" />
              <div className="report-grid">
                {Object.entries(detail.status_breakdown).map(([status, count]) => (
                  <div className="process-mini-metric" key={status}>
                    <span>{status}</span>
                    <strong>{count}</strong>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          {Object.keys(detail.pack_breakdown).length > 0 ? (
            <section className="employer-section">
              <SectionTitle label="Assessment packs" />
              <div className="report-grid">
                {Object.entries(detail.pack_breakdown).map(([pack, count]) => (
                  <div className="process-mini-metric" key={pack}>
                    <span>{pack}</span>
                    <strong>{count}</strong>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          <section className="employer-section">
            <div className="section-title">
              <h2>Attempts</h2>
            </div>
            <div className="attempt-table">
              <div className="attempt-row table-head">
                <span>Candidate</span>
                <span>Status</span>
                <span>Pack</span>
                <span>Submitted</span>
                <span>Score</span>
                <span>Report</span>
              </div>
              {detail.attempts.map((a) => (
                <div className="attempt-row" key={a.id}>
                  <div className="attempt-email-meta">
                    <span>{a.candidate_email ?? "No email"}</span>
                    <span className="attempt-sent-at">{timeAgo(a.created_at)}</span>
                  </div>
                  <span>
                    <span className={`status-pill ${a.status === "submitted" ? "ready" : a.status === "expired" ? "error" : "warn"}`}>
                      {a.status}
                    </span>
                  </span>
                  <span className="attempt-sent-at">{a.assessment_pack_slug ?? "—"}</span>
                  <span className="attempt-sent-at">{a.submitted_at ? timeAgo(a.submitted_at) : "—"}</span>
                  <span><ScoreBadge score={a.score_total} /></span>
                  {a.report_id ? (
                    <Link className="command-button secondary" href={`/admin/reports/${a.id}`}>
                      View report
                    </Link>
                  ) : (
                    <span className="empty-state">No report</span>
                  )}
                </div>
              ))}
              {!detail.attempts.length ? (
                <p className="empty-state">No attempts for this employer.</p>
              ) : null}
            </div>
          </section>
        </>
      ) : null}
    </main>
  );
}

function SectionTitle({ label }: { label: string }) {
  return (
    <div className="section-title">
      <div><h2>{label}</h2></div>
    </div>
  );
}