# SignalLoop Web

Candidate-facing workspace and employer review portal for the SignalLoop MVP.

## Local commands

```sh
npm install
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run dev -- -H 127.0.0.1 --port 3000
```

Open a candidate invite at:

```text
http://127.0.0.1:3000/invite/{invite_token}
```

Open the employer portal at:

```text
http://127.0.0.1:3000/employer
```

The workspace calls the API directly to load/save candidate files, run public tests, and ask the constrained AI collaborator. Public test results are persisted by the API for evidence reports.

The employer portal requires Clerk locally and in production. Candidate invite links do
not require a candidate account.

See `../../docs/development/testing.md` for browser test commands and `../../docs/deployment/render-supabase-clerk.md` for hosted env setup.
