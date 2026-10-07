# Factory V3 Agent Protocol v1

## Polling

The local runner polls the control plane at a configurable interval (default 15 seconds).
It MUST also perform an immediate poll after completing a command and after recovering from a crash.

## Command lifecycle

`QUEUED -> CLAIMED -> RUNNING -> SUCCEEDED|FAILED|BLOCKED`

The runner claims a command by moving/recording it under `control/processing/` and adding:
- `claimed_at`
- `worker_pid`
- `attempt`

A command is idempotent by `command_id`.

## Result publication

After execution, publish:
1. `control/outbox/<command_id>.json`
2. update `control/state.json`
3. update `control/reports/latest.md`
4. append a bounded snapshot under `control/reports/history/`

## Crash recovery

On startup:
- read `control/processing/`
- detect stale RUNNING commands by heartbeat/TTL
- mark them recoverable
- resume or requeue according to command policy
- publish a recovery event

The runner MUST NOT deadlock because a worker died.

## Report contract

Every result/report MUST include:
- command_id
- job_id
- timestamp
- project
- action
- status
- exact error (when failed)
- files changed
- commit SHA
- PR number/URL
- CI status/run ID
- deploy status/id
- live verification status
- next_action

No invented PASS status is allowed. Unknown/not-proven states must remain explicit.

## Secrets

The control plane must never contain secrets or token values. Redact environment values from logs.
