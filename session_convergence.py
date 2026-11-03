#!/usr/bin/env python3
"""
session_convergence.py — Factory V3: Session convergence enforcement.

Implements the P0 convergence guards:
- Per-agent-type iteration budgets (max_steps)
- Progress tracking (last_progress, steps_without_progress)
- Budget exceeded detection
- No-progress stuck detection
- Session persistence to disk (state.json)
- Recovery with counter reset

Designed to be imported by f3.py worker_tick / execute_one or used standalone
in tests. All state is persisted to disk under a sessions/ directory so that
a session survives worker/Factory restarts.
"""

import os, json, time, uuid
from datetime import datetime, timezone
from pathlib import Path

# Agent type -> max steps budget (loaded from autonomy config at runtime)
# Default values per P0 mission: ~5 for short analysis, ~12 for implementation.
AGENT_BUDGETS = {
    "general-fast": 5,
    "rfast": 5,
    "rbalanced": 8,
    "rdeep": 12,
    "rvision": 12,
    "rreview": 8,
    "maintenance-factory": 10,
    "web-research": 7,
    "ui-playwright": 10,
    "seo-analytics": 7,
}

DEFAULT_MAX_STEPS = 5
NO_PROGRESS_STEPS = 5
SESSIONS_DIR_NAME = "sessions"


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def now_epoch():
    return time.time()


class SessionConvergence:
    """Tracks per-session iteration budget and progress for convergence enforcement.

    Each session has:
      - iteration_count: incremented on each major operation/retry
      - max_steps: budget from agent_type (see AGENT_BUDGETS)
      - agent_type: used to look up budget
      - last_progress: ISO timestamp of last meaningful progress
      - steps_without_progress: counter, resets on record_progress()
      - status: active, recovering, parked, completed, failed
    """

    def __init__(self, sessions_dir=None):
        if sessions_dir is None:
            # Default: sessions/ under the factory state root
            root = os.environ.get("F3_ROOT", r"C:\factory-service")
            sessions_dir = os.path.join(root, "state", SESSIONS_DIR_NAME)
        self.sessions_dir = sessions_dir
        os.makedirs(self.sessions_dir, exist_ok=True)
        self._sessions = {}  # session_id -> session dict
        self._load_all()

    # ── Path helpers ──────────────────────────────────────────────
    def _session_dir(self, session_id):
        return os.path.join(self.sessions_dir, session_id)

    def _state_file(self, session_id):
        return os.path.join(self._session_dir(session_id), "state.json")

    # ── Load / persist ────────────────────────────────────────────
    def _load_all(self):
        self._sessions = {}
        if not os.path.isdir(self.sessions_dir):
            return
        for name in os.listdir(self.sessions_dir):
            sf = os.path.join(self.sessions_dir, name, "state.json")
            if os.path.isfile(sf):
                try:
                    with open(sf, encoding="utf-8") as f:
                        s = json.load(f)
                    self._sessions[s["session_id"]] = s
                except Exception:
                    # Corrupt or incomplete state file: skip, do not crash
                    pass

    def _persist(self, session):
        d = self._session_dir(session["session_id"])
        os.makedirs(d, exist_ok=True)
        sf = self._state_file(session["session_id"])
        tmp = sf + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2, ensure_ascii=False)
        os.replace(tmp, sf)
        self._sessions[session["session_id"]] = session

    # ── Session lifecycle ─────────────────────────────────────────
    def create_session(self, session_id, task_id, agent_type="general-fast",
                       max_steps=None, **extra):
        """Create a new session with iteration budget.

        If agent_type is unknown, falls back to DEFAULT_MAX_STEPS (deterministic).
        """
        if max_steps is None:
            max_steps = AGENT_BUDGETS.get(agent_type, DEFAULT_MAX_STEPS)
        session = {
            "session_id": session_id,
            "task_id": task_id,
            "agent_type": agent_type,
            "max_steps": max_steps,
            "iteration_count": 0,
            "status": "active",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "heartbeat": now_iso(),
            "last_progress": now_iso(),
            "steps_without_progress": 0,
            "retry_count": 0,
        }
        session.update(extra)
        self._persist(session)
        return session

    def get_session(self, session_id):
        return self._sessions.get(session_id)

    def record_progress(self, session_id):
        """Record meaningful progress: resets steps_without_progress to 0."""
        s = self._sessions.get(session_id)
        if not s:
            return False
        s["last_progress"] = now_iso()
        s["steps_without_progress"] = 0
        s["updated_at"] = now_iso()
        self._persist(s)
        return True

    def increment_iteration(self, session_id):
        """Increment iteration count and steps_without_progress.

        Call this after each major operation or retry.
        Returns the updated session dict.
        """
        s = self._sessions.get(session_id)
        if not s:
            return None
        s["iteration_count"] = s.get("iteration_count", 0) + 1
        s["steps_without_progress"] = s.get("steps_without_progress", 0) + 1
        s["retry_count"] = s.get("retry_count", 0) + 1
        s["updated_at"] = now_iso()
        self._persist(s)
        return s

    def check_budget(self, session_id):
        """Check if session has exceeded budget or is stuck without progress.

        Returns dict: {exceeded: bool, reason: str, iteration_count: int,
                       max_steps: int, steps_without_progress: int}
        """
        s = self._sessions.get(session_id)
        if not s:
            return {"exceeded": False, "reason": "no_session",
                    "iteration_count": 0, "max_steps": 0,
                    "steps_without_progress": 0}

        max_steps = s.get("max_steps", DEFAULT_MAX_STEPS)
        iteration_count = s.get("iteration_count", 0)
        swop = s.get("steps_without_progress", 0)

        if iteration_count >= max_steps:
            return {
                "exceeded": True,
                "reason": f"iteration_budget_exceeded ({iteration_count} >= {max_steps})",
                "iteration_count": iteration_count,
                "max_steps": max_steps,
                "steps_without_progress": swop,
            }
        if swop >= NO_PROGRESS_STEPS:
            return {
                "exceeded": True,
                "reason": f"no_progress_last_n_steps ({swop} >= {NO_PROGRESS_STEPS})",
                "iteration_count": iteration_count,
                "max_steps": max_steps,
                "steps_without_progress": swop,
            }
        return {
            "exceeded": False,
            "reason": "within_budget",
            "iteration_count": iteration_count,
            "max_steps": max_steps,
            "steps_without_progress": swop,
        }

    def recover_session(self, session_id):
        """Recover a session: reset iteration and progress counters.

        Called after a crash/restart to give the session a fresh start
        while preserving its identity and agent type.
        """
        s = self._sessions.get(session_id)
        if not s:
            return None
        s["status"] = "recovering"
        s["iteration_count"] = 0
        s["steps_without_progress"] = 0
        s["retry_count"] = s.get("retry_count", 0) + 1
        s["heartbeat"] = now_iso()
        s["updated_at"] = now_iso()
        self._persist(s)
        return s

    def complete_session(self, session_id, success=True, result=None):
        """Mark session as completed or failed with result."""
        s = self._sessions.get(session_id)
        if not s:
            return None
        s["status"] = "completed" if success else "failed"
        s["result"] = result or {}
        s["updated_at"] = now_iso()
        s["ended_at"] = now_iso()
        self._persist(s)
        return s

    def park_session(self, session_id, reason="parked"):
        """Park a session (terminal state, no automatic restart)."""
        s = self._sessions.get(session_id)
        if not s:
            return None
        s["status"] = "parked"
        s["park_reason"] = reason
        s["updated_at"] = now_iso()
        self._persist(s)
        return s

    def list_sessions(self):
        return list(self._sessions.values())

    def sessions_by_status(self, status):
        return [s for s in self._sessions.values() if s.get("status") == status]


# ── Standalone CLI for inspection ─────────────────────────────────
if __name__ == "__main__":
    import sys
    sc = SessionConvergence()
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        for s in sc.list_sessions():
            print(json.dumps(s, indent=2, ensure_ascii=False))
    else:
        print("Usage: python session_convergence.py list")
