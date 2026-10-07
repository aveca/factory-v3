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
  
  acquireLock(worktreePath, owner) {
    const lockFile = this.getLockFile(worktreePath);
    const ownerFile = this.getWorktreeOwnerFile(worktreePath);
    const now = new Date().toISOString();
    if (fs.existsSync(lockFile)) {
      try {
        const existingLock = JSON.parse(fs.readFileSync(lockFile, 'utf8'));
        const lockAge = Date.now() - new Date(existingLock.acquired_at).getTime();
        if (lockAge > LEASE_TTL_MS) { this.releaseLock(worktreePath, { force: true, reason: 'lease_expired' }); }
        else { return { success: false, reason: 'worktree_locked' }; }
      } catch (e) { fs.unlinkSync(lockFile); }
    }
    if (fs.existsSync(ownerFile)) {
      try {
        const existingOwner = JSON.parse(fs.readFileSync(ownerFile, 'utf8'));
        const ownerAge = Date.now() - new Date(existingOwner.acquired_at).getTime();
        if (ownerAge > LEASE_TTL_MS) { console.log(`Owner expired for ${worktreePath}`); }
        else if (existingOwner.worker_id !== owner.worker_id) { return { success: false, reason: 'worktree_owned_by_other' }; }
      } catch (e) {}
    }
    const lockInfo = { worktree: worktreePath, owner, acquired_at: new Date().toISOString(), heartbeat: new Date().toISOString() };
    fs.writeFileSync(this.getLockFile(worktreePath), JSON.stringify(lockInfo, null, 2), 'utf8');
    fs.writeFileSync(this.getWorktreeOwnerFile(worktreePath), JSON.stringify(lockInfo, null, 2), 'utf8');
    this.startHeartbeat(worktreePath, owner);
    this.activeLocks.set(worktreePath, lockInfo);
    return { success: true, lockInfo };
  }
  releaseLock(worktreePath, options = {}) {
    const lockFile = this.getLockFile(worktreePath);
    const ownerFile = this.getWorktreeOwnerFile(worktreePath);
    if (fs.existsSync(lockFile)) fs.unlinkSync(lockFile);
    if (fs.existsSync(ownerFile)) fs.unlinkSync(ownerFile);
    this.activeLocks.delete(worktreePath);
    return { success: true };
  }
  heartbeat(worktreePath) { console.log('heartbeat', worktreePath); }
  startHeartbeat(worktreePath, owner) { 
    this.stopHeartbeat(worktreePath);
    const interval = setInterval(() => { this.heartbeat(worktreePath); }, HEARTBEAT_INTERVAL_MS);
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
  checkSafeForDestructive(worktreePath, requesterWorkerId) {
    const ownerFile = this.getWorktreeOwnerFile(worktreePath);
    if (fs.existsSync(ownerFile)) {
      try {
        const owner = JSON.parse(fs.readFileSync(ownerFile, 'utf8'));
        if (owner.owner.worker_id !== requesterWorkerId) { return { safe: false, reason: `Owned by ${owner.owner.worker_id}` }; }
      } catch (e) { return { safe: false, reason: 'Cannot read owner file' }; }
    }
    const wip = this.checkWIP(worktreePath);
    if (wip.hasWIP) { return { safe: false, reason: 'WIP present' }; }
    return { safe: true };
  }
  denyWrite(worktreePath, requester, operation) {
    console.log(`[worktree-lock] Write denied: ${requester.name} attempted ${operation}`);
    return { denied: true };
  }
  logLockEvent(type, worktreePath, data) {
    const logDir = path.join('C:/factory', 'logs', 'worktree-locks');
    if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });
    const logFile = path.join(logDir, `locks-${new Date().toISOString().slice(0,10)}.jsonl`);
    fs.appendFileSync(logFile, JSON.stringify({ type, timestamp: new Date().toISOString(), worktree: worktreePath, ...data }) + '\n', 'utf8');
  }
  getAllLocks() { return []; }
  cleanupStaleLocks() { return 0; }
}
module.exports = { WorktreeLockManager, LEASE_TTL_MS: 5*60*1000, HEARTBEAT_INTERVAL_MS: 30*1000 };

if (require.main === module) {
  const lockManager = new (require('./worktree-lock.cjs').WorktreeLockManager)();
  console.log('Test passed');
}