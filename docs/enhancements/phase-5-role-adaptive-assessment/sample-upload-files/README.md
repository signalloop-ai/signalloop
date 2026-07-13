# Sample Upload Files

Use these files to test Adaptive Builder JD upload.

- `senior-backend-ai-infra-jd.txt`
- `senior-backend-ai-infra-jd.docx`
- `senior-backend-ai-infra-jd.pdf`
- `frontend-platform-engineer-jd.docx`
- `frontend-platform-engineer-jd.pdf`
- `data-engineer-analytics-platform-jd.docx`
- `data-engineer-analytics-platform-jd.pdf`

Expected results:

- Senior backend AI infra JD: invite-ready Advanced FastAPI adaptive blueprint.
- Frontend platform JD: planned/future frontend assessment blueprint, not backend.
- Data engineer analytics platform JD: planned/future data assessment blueprint or
  future coverage, not backend.

Notes:

- DOCX and TXT should extract reliably.
- PDFs are intentionally text-based, not scanned, so the current MVP parser can extract them.
- Legacy binary `.doc` is not supported by the uploader. Use `.docx` instead.
