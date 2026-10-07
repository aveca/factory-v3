const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const FACTORY_DIR = 'C:/factory';
const WORKTREES_BASE = path.join(FACTORY_DIR, 'worktrees');
const LOCKS_DIR = path.join(FACTORY_DIR, 'locks');
const LEASE_TTL_MS = 5 * 60 * 1000;
const HEARTBEAT_INTERVAL_MS = 30 * 1000;

class WorktreeLockManager {
  constructor() {
    this.activeLocks = new Map();
    this.heartbeatIntervals = new Map();
    this.ensureDirs();
  }
  ensureDirs() {
    if (!fs.existsSync(LOCKS_DIR)) fs.mkdirSync(LOCKS_DIR, { recursive: true });
    if (!fs.existsSync(WORKTREES_BASE)) fs.mkdirSync(WORKTREES_BASE, { recursive: true });
  }
  getLockFile(worktreePath) {
    const worktreeName = path.basename(worktreePath);
    const projectName = path.basename(path.dirname(worktreePath));
    const lockDir = path.join(LOCKS_DIR, projectName);
    if (!fs.existsSync(lockDir)) fs.mkdirSync(lockDir, { recursive: true });
    return path.join(lockDir, `${path.basename(worktreePath)}.lock.json`);
  }
  getWorktreeOwnerFile(worktreePath) { return path.join(worktreePath, '.worktree-owner.json'); }
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
  checkWIP(worktreePath) {
    try {
      const status = execFileSync('git', ['status', '--porcelain'], { cwd: worktreePath, encoding: 'utf8', timeout: 10000, windowsHide: true });
      return { hasWIP: status.trim().length > 0 };
    } catch (e) { return { hasWIP: false }; }
  }
}
module.exports = { WorktreeLockManager, LEASE_TTL_MS: 5*60*1000, HEARTBEAT_INTERVAL_MS: 30*1000 };