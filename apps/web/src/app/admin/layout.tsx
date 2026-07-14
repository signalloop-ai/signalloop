"use client";

import { SignInButton, UserButton, useAuth, useUser } from "@clerk/nextjs";
import { Loader2, LogIn, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { fetchAdminMe } from "./api";

const Logo = () => (
  <svg className="topbar-logo" width="30" height="30" viewBox="0 0 30 30" fill="none" aria-label="SignalLoop">
    <rect width="30" height="30" rx="7" fill="#3b82f6" />
    <path d="M15 6C19.97 6 24 10.03 24 15C24 19.97 19.97 24 15 24C10.5 24 6.8 20.7 6.1 16.4" stroke="white" strokeWidth="2.3" strokeLinecap="round" />
    <path d="M4.5 14.5L6.2 17.2L9 15.5" stroke="white" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="15" cy="6" r="2" fill="#22d3ee" />
  </svg>
);

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { isLoaded, isSignedIn, user } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();
  const [authState, setAuthState] = useState<"loading" | "admin" | "not_admin" | "signed_out">("loading");
  const signedInEmail = user?.primaryEmailAddress?.emailAddress ?? user?.emailAddresses[0]?.emailAddress;

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    let cancelled = false;
    (async () => {
      try {
        const me = await fetchAdminMe(getToken);
        if (!cancelled) {
          setAuthState(me.role === "super_admin" ? "admin" : "not_admin");
        }
      } catch {
        if (!cancelled) setAuthState("not_admin");
      }
    })();
    return () => { cancelled = true; };
  }, [isLoaded, isSignedIn, getToken]);

  if (!isLoaded) {
    return (
      <main className="employer-page">
        <p className="empty-state">Loading…</p>
      </main>
    );
  }

  if (!isSignedIn) {
    return (
      <main className="employer-page">
        <section className="employer-auth">
          <div className="employer-brand">
            <Logo />
            <div>
              <h1>SignalLoop</h1>
              <p>Super Admin Portal</p>
            </div>
          </div>
          <div className="auth-status">
            <ShieldCheck size={18} aria-hidden="true" />
            <span>Sign in with an admin account to continue.</span>
          </div>
          <SignInButton mode="modal">
            <button className="command-button primary">
              <LogIn size={18} aria-hidden="true" />
              Sign in
            </button>
          </SignInButton>
        </section>
      </main>
    );
  }

  if (authState === "loading") {
    return (
      <main className="employer-page">
        <p className="empty-state"><Loader2 size={16} className="spin" aria-hidden="true" /> Verifying admin access…</p>
      </main>
    );
  }

  if (authState === "not_admin" || authState === "signed_out") {
    router.replace("/employer");
    return (
      <main className="employer-page">
        <p className="empty-state">Redirecting to employer portal…</p>
      </main>
    );
  }

  return (
    <>
      <header className="employer-header">
        <div className="employer-brand">
          <Logo />
          <div>
            <h1>SignalLoop</h1>
            <p>Super Admin Portal</p>
          </div>
        </div>
        <div className="action-row">
          <div className="admin-identity">
            <span className="status-pill ready">Super Admin</span>
            {signedInEmail ? <span className="attempt-sent-at">{signedInEmail}</span> : null}
          </div>
          <UserButton />
        </div>
      </header>
      {children}
    </>
  );
}
