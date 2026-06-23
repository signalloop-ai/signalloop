"use client";

import { useAuth } from "@clerk/nextjs";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { fetchAdminEmployers } from "./api";
import type { AdminEmployerSummary } from "./types";

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
  return <span className={`status-pill ${cls}`}>{score.toFixed(1)}</span>;
}

export default function AdminRosterPage() {
  const { getToken } = useAuth();
  const [employers, setEmployers] = useState<AdminEmployerSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setEmployers(await fetchAdminEmployers(getToken));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load employers");
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => void refresh(), 60_000);
    return () => window.clearInterval(interval);
  }, [refresh]);

  return (
    <main className="employer-page">
      <section className="employer-section">
        <div className="section-title">
          <h2>Employers</h2>
          {loading ? <span className="autosave-chip">Refreshing…</span> : null}
        </div>

        {error ? <p className="submission-error">{error}</p> : null}

        <div className="attempt-table">
          <div className="attempt-row table-head">
            <span>Employer</span>
            <span>Role</span>
            <span>Created</span>
            <span>Last activity</span>
            <span>Invites</span>
            <span>Submitted</span>
            <span>Reports</span>
            <span>Avg score</span>
          </div>
          {employers.map((emp) => (
            <Link
              href={`/admin/employers/${emp.id}`}
              key={emp.id}
              className="attempt-row admin-employer-row"
            >
              <div className="attempt-email-meta">
                <span>{emp.email}</span>
                {emp.company_name ? (
                  <span className="attempt-sent-at">{emp.company_name}</span>
                ) : null}
              </div>
              <span>
                {emp.role === "super_admin" ? (
                  <span className="status-pill ready">Admin</span>
                ) : (
                  <span className="status-pill">Employer</span>
                )}
              </span>
              <span className="attempt-sent-at">{timeAgo(emp.created_at)}</span>
              <span className="attempt-sent-at">{timeAgo(emp.last_activity_at)}</span>
              <span>{emp.invite_count}</span>
              <span>{emp.submitted_count}</span>
              <span>{emp.report_count}</span>
              <span>
                <ScoreBadge score={emp.avg_score} />
              </span>
            </Link>
          ))}
          {!employers.length && !loading ? (
            <p className="empty-state">No employers found.</p>
          ) : null}
          {loading && !employers.length ? (
            <p className="empty-state"><Loader2 size={16} className="spin" aria-hidden="true" /> Loading employers…</p>
          ) : null}
        </div>
      </section>
    </main>
  );
}