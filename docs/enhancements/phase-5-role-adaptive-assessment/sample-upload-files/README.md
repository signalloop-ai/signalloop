# Sample Upload Files

Use these files to test Adaptive Builder JD upload.

- `senior-backend-ai-infra-jd.txt`
- `senior-backend-ai-infra-jd.docx`
- `senior-backend-ai-infra-jd.pdf`

Expected result: an invite-ready Advanced FastAPI adaptive blueprint.

Notes:

- DOCX and TXT should extract reliably.
- The PDF is intentionally text-based, not scanned, so the current MVP parser can
  extract it.
- Legacy binary `.doc` is not supported by the uploader. Use `.docx` instead.
