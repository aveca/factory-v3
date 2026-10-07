class WorktreeLockManager {
  constructor() {
    this.activeLocks = new Map();
    this.heartbeatIntervals = new Map();
  }
  acquireLock(worktreePath, owner) { return { success: true }; }
  releaseLock(worktreePath, options = {}) { return { success: true }; }
  heartbeat(worktreePath) { console.log('heartbeat', worktreePath); }
  startHeartbeat(worktreePath, owner) { 
    this.stopHeartbeat(worktreePath);
    const interval = setInterval(() => { this.heartbeat(worktreePath); }, 1000);
    this.heartbeatIntervals.set(worktreePath, interval);
  }
  stopHeartbeat(worktreePath) {
    const interval = this.heartbeatIntervals.get(worktreePath);
    if (interval) { clearInterval(interval); this.heartbeatIntervals.delete(worktreePath); }
  }
  checkWIP() { return { hasWIP: false }; }
}
module.exports = { WorktreeLockManager };