# Factory V3 — Shared Control Plane

This repository is the shared control plane between the local Factory V3 runtime and external operators/agents.

## Contract

- `control/state.json` = current authoritative factory state.
- `control/desired-state.json` = requested operating mode / target condition.
- `control/inbox/*.json` = commands waiting for the local runner.
- `control/processing/*.json` = commands currently claimed by the runner.
- `control/outbox/*.json` = command results.
- `control/reports/latest.md` = latest human-readable operational report.
- `control/reports/history/` = immutable report snapshots.
- `control/heartbeat.json` = local runner heartbeat.
- Commands and state MUST carry `job_id`, `command_id`, `timestamp`, and repository/project scope where applicable.

## Ownership

The local runner owns execution and writes state/results/reports.
The external operator may read all control-plane files and may create commands in `control/inbox/`.

The runner MUST NOT claim a command unless it is valid JSON, targeted to an allowed project, and not already completed.

## Safety

Never put secrets, tokens, credentials, cookies, or private keys in the control plane.
Do not store full noisy logs in `state.json`; use report files and bounded event files.

## Goal

The human operator should not copy/paste reports between the local factory and the external operator. The local runner continuously publishes machine-readable state and the latest report, and continuously consumes commands from this repository.
