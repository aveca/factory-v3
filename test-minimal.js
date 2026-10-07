class WorktreeLockManager {
  constructor() {
    this.activeLocks = new Map();
  }
  acquireLock() { return { success: true }; }
  releaseLock() { return { success: true }; }
  heartbeat(worktreePath) {
    console.log('heartbeat', worktreePath);
  }
  startHeartbeat() { return setInterval(() => {}, 1000); }
  stopHeartbeat() {}
  checkWIP() { return { hasWIP: false }; }
}
module.exports = { WorktreeLockManager };