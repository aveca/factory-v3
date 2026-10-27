#!/usr/bin/env python3
"""
watchdog_convergence.py — Factory V3: Watchdog based on last effective progress.

Detects sessions that are stuck despite having a live process:
  - no_progress_last_n_steps: steps_without_progress >= NO_PROGRESS_STEPS
  - iteration_budget_exceeded: iteration_count >= max_steps

Integrates with SessionConvergence to mark sessions as stuck/parked,
preventing a blocked sub-agent from retaining the parent mission indefinitely.
"""

import os, json, time
from datetime import datetime, timezone
from session_convergence import (
    SessionConvergence, NO_PROGRESS_STEPS, now_iso, now_epoch
)

MAX_RETRIES = 3


class WatchdogConvergence:
    """Watchdog that checks session progress and budget, not just process liveness.

    A session is considered stuck if:
      1. steps_without_progress >= NO_PROGRESS_STEPS (no meaningful progress)
      2. iteration_count >= max_steps (budget exhausted)

    When stuck, the session is parked (terminal state) after MAX_RETRIES.
    """

    def __init__(self, session_convergence=None, max_retries=MAX_RETRIES):
        self.sc = session_convergence or SessionConvergence()
        self.max_retries = max_retries

    def check_session(self, session_id):
        """Check a single session for stuck conditions.

        Returns list of issue dicts (empty if session is healthy).
        """
        s = self.sc.get_session(session_id)
        if not s:
            return []
        issues = []
        budget = self.sc.check_budget(session_id)
        if budget["exceeded"]:
            issues.append({
                "type": budget["reason"].split(" ")[0].replace("(", ""),
                "session_id": session_id,
                "iteration_count": budget["iteration_count"],
                "max_steps": budget["max_steps"],
                "steps_without_progress": budget["steps_without_progress"],
                "reason": budget["reason"],
                "detected_at": now_iso(),
            })
        return issues

    def handle_stuck(self, session_id, issues):
        """Handle stuck sessions: log, increment retries, park if max exceeded.

        Returns the session dict after handling, or None if not found.
        """
        s = self.sc.get_session(session_id)
        if not s:
            return None

        # Log stuck events
        for issue in issues:
            self._log_stuck(session_id, issue)

        # Determine action
        budget = self.sc.check_budget(session_id)
        if budget["exceeded"]:
            if s.get("retry_count", 0) >= self.max_retries:
                self.sc.park_session(session_id, reason=budget["reason"])
                self._log_parked(session_id, budget["reason"])
            else:
                # Recovery: reset counters but increment retry
                self.sc.recover_session(session_id)
                self._log_recover(session_id, budget["reason"])
        return self.sc.get_session(session_id)

    def check_all(self):
        """Check all active sessions for stuck conditions.

        Returns dict: {session_id: [issues], ...} for sessions with issues.
        """
        results = {}
        for s in self.sc.list_sessions():
            if s.get("status") not in ("active", "recovering"):
                continue
            issues = self.check_session(s["session_id"])
            if issues:
                results[s["session_id"]] = issues
                self.handle_stuck(s["session_id"], issues)
        return results

    # ── Logging helpers ──────────────────────────────────────────
    def _log_stuck(self, session_id, issue):
        s = self.sc.get_session(session_id)
        if not s:
            return
        d = self.sc._session_dir(session_id)
        os.makedirs(d, exist_ok=True)
        log_file = os.path.join(d, "watchdog.jsonl")
        entry = {
            "event": "WORKER_STUCK",
            "session_id": session_id,
            "timestamp": now_iso(),
            "issue": issue,
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _log_parked(self, session_id, reason):
        s = self.sc.get_session(session_id)
        if not s:
            return
        d = self.sc._session_dir(session_id)
        os.makedirs(d, exist_ok=True)
        log_file = os.path.join(d, "watchdog.jsonl")
        entry = {
            "event": "SESSION_PARKED",
            "session_id": session_id,
            "timestamp": now_iso(),
            "reason": reason,
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _log_recover(self, session_id, reason):
        s = self.sc.get_session(session_id)
        if not s:
            return
        d = self.sc._session_dir(session_id)
        os.makedirs(d, exist_ok=True)
        log_file = os.path.join(d, "watchdog.jsonl")
        entry = {
            "event": "SESSION_RECOVERING",
            "session_id": session_id,
            "timestamp": now_iso(),
            "reason": reason,
            "retry_count": s.get("retry_count", 0),
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── Standalone CLI ─────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sc = SessionConvergence()
    wd = WatchdogConvergence(sc)
    results = wd.check_all()
    if results:
        for sid, issues in results.items():
            print(f"STUCK: {sid} -> {[i['reason'] for i in issues]}")
    else:
        print("No stuck sessions detected.")
