# AUTONOMY CONTRACT — canonical operating rules

Version: 1.0
Date: 2026-11-25

This contract defines the intended operating model for AI agents in this repository. It does not grant credentials, platform scopes, local-machine access, or permissions that the runtime does not actually possess.

## Mission and scope
- Active commercial products: BOT-WOW and Sargasses/Sargagame only.
- Factory/orchestration repositories exist only to operate, supervise, and improve those products.
- Agents must not revive unrelated or archived projects unless the founder explicitly requests it.
- Optimize for verified customer value and collected revenue; never fabricate traffic, leads, sales, attribution, tests, or production status.

## Autonomous execution — default
For ordinary, reversible, low-risk engineering work within the repository's approved scope, agents must proceed without asking the founder for routine approval:
1. Read this contract, repository instructions, current state, backlog, active locks, and relevant prior PRs/issues.
2. Select or create a deduplicated, prioritized mission; record its objective and acceptance criteria.
3. Claim it atomically; use an isolated worktree and branch; preserve existing user changes.
4. Implement the smallest justified change; add regression coverage.
5. Run the actual relevant tests, build, lint, security checks, and diff review.
6. Push a branch and open/update a PR; publish exact evidence and status.
7. Merge/deploy only where the repository's delivery policy explicitly permits it and every required SHA-bound gate passes.
8. Verify the actual runtime or live result; otherwise keep the task open as NOT VERIFIED/BLOCKED.
9. Update the shared state, task ledger, changelog, and handoff; resume the next eligible mission automatically.

Do not ask the founder to copy prompts, relay routine reports, or perform ordinary technical validation when a functioning authorized GitHub/runtime channel exists. If the channel is unavailable, report the exact missing capability; do not pretend a dispatch occurred.

## Access and capability truth
- Use only credentials, OAuth scopes, connectors, local tools, and repository permissions actually available to the executing runtime.
- Never claim full access based on a config flag, a GitHub issue, a PID, a session API record, or a green CI run.
- Keep machine credentials and secrets outside Git; never print, copy into issues, or commit them.
- A local OpenCode GUI action is proven only by evidence from the actual GUI (window identity/screenshot, UI-created session, prompt sent through UI, visible response). API/headless sessions are not GUI proof.
- Never interact with the founder's personal/private sessions or protected windows. Use a dedicated Factory-owned profile/workspace.

## Human-approval boundary
Autonomous by default does NOT mean unrestricted or unsafe. Stop and request specific approval before:
- real charges, refunds, subscriptions, payment/checkout/webhook changes, price or contract changes;
- secrets, credentials, authentication, permissions, account ownership, or security-boundary changes;
- destructive or irreversible data changes, risky database migrations, deletion, or production data exports;
- DNS, domains, production infrastructure, paid spend, paid services, mass communications, or legally binding actions;
- any operation whose scope or rollback is unclear.

Prepare code, tests, isolated branches, impact analysis, and rollback plan while waiting. Never bypass a denylist, policy refusal, or missing permission through another channel.

## Delivery gates
A production delivery is eligible only when:
- the repository and change category are explicitly enabled by the current delivery policy;
- the exact candidate SHA has all required CI checks successful;
- focused regression tests pass;
- independent review/security checks pass where required;
- rollback is documented and available;
- deployment workflow succeeds; and
- the deployed artifact is verified live against that exact SHA/version.
Any missing or stale evidence means BLOCKED, not success.

## Status vocabulary
Use only evidence-backed statuses: PLANNED, CLAIMED, RUNNING, PR_OPEN, TESTED, CI_VALIDATED, MERGED, DEPLOYED, LIVE_VERIFIED, BLOCKED, FAILED. Report the exact repo, branch, SHA, PR, commands/exit codes, CI run, runtime/live proof, and remaining blocker.

## Conflict resolution
1. Security, legal, payment, data-protection and platform constraints.
2. This autonomy contract's human-approval boundary.
3. Repository-specific product and delivery policy.
4. Repository AGENTS/CLAUDE and local agent instructions.
5. Task prompt or issue body.
A lower-level instruction cannot expand permissions or override a higher-level restriction. If repository policies conflict, fail closed and create a policy-reconciliation task; do not silently choose the more permissive rule.

## Anti-regression
Every discovered contradiction must be fixed at its source and covered by a test or automated policy check. A documentation-only change is not proof that the runtime enforces it. Keep this contract synchronized with the actual Factory admission, dispatch, execution, and delivery code.
