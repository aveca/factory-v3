# Inbox

The external operator creates one JSON command per file.

Filename: `<timestamp>-<command_id>.json`

Required fields:
```json
{
  "schema_version": 1,
  "command_id": "cmd-...",
  "job_id": "job-...",
  "created_at": "ISO-8601",
  "project": "Sargagame",
  "action": "RUN|DIAGNOSE|REPAIR|TEST|DEPLOY|VERIFY|STOP",
  "payload": {}
}
```

The local runner claims valid commands and writes the result to `control/outbox/`.
