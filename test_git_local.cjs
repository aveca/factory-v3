const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Test git operations in the test worktree
try {
  const status = execSync('git status --porcelain', { encoding: 'utf8', cwd: 'C:\\\\factory\\\\worktrees\\\\test-sargagame', timeout: 10000 }).trim();
  console.log('Status in test worktree:', status ? status : 'empty (no changes)');
} catch(e) {
  console.log('Error:', e.message.substring(0, 60));
}

// Test git diff
try {
  const diff = execSync('git diff', { encoding: 'utf8', cwd: 'C:\\\\factory\\\\worktrees\\\\test-sargagame', timeout: 10000 }).trim();
  console.log('Git diff:', diff ? diff.substring(0, 200) : 'no diff');
} catch(e) {
  console.log('Diff error:', e.message.substring(0, 60));
}

// Test git add + commit
try {
  // Make a test file modification
  const testFile = path.join('C:\\\\factory\\\\worktrees\\\\test-sargagame', 'test-mod.txt');
  fs.writeFileSync(testFile, 'Factory V3 test modification\n');
  const add = execSync('git add test-mod.txt', { encoding: 'utf8', cwd: 'C:\\\\factory\\\\worktrees\\\\test-sargagame', timeout: 10000 }).trim();
  console.log('Git add:', add);
  const commit = execSync('git commit -m Factory-test-mod-local', { encoding: 'utf8', cwd: 'C:\\\\factory\\\\worktrees\\\\test-sargagame', timeout: 10000 }).trim();
  console.log('Git commit:', commit.substring(0, 80));
  const sha = execSync('git rev-parse HEAD', { encoding: 'utf8', cwd: 'C:\\\\factory\\\\worktrees\\\\test-sargagame', timeout: 10000 }).trim();
  console.log('Commit SHA:', sha.substring(0, 80));
} catch(e) {
  console.log('Commit error:', e.message.substring(0, 80));
}