import { ArrowRight, BriefcaseBusiness } from "lucide-react";
import Link from "next/link";

export default function Home() {
  return (
    <main className="onboarding">
      <section className="onboarding-panel">
        <div>
          <h1>SignalLoop Candidate Workspace</h1>
          <p>
            Open an invite link to start an assessment workspace. Candidate access uses a
            unique invite token and does not require login.
          </p>
        </div>
        <Link className="command-button primary" href="/employer">
          <BriefcaseBusiness size={18} aria-hidden="true" />
          Open employer portal
        </Link>
        <p>
          Candidate workspaces require a real invite URL generated from the employer portal.
        </p>
      </section>
    </main>
  );
}
