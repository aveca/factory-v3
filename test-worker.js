// test-worker.js
const { spawn } = require('child_process');
const { execFileSync } = require('child_process');

// Get current branch from worktree
const worktree = 'C:\\factory\\worktrees\\sargagame\\sargagame-1791302731862-jcjhm3';
const branch = execFileSync('git', ['branch', '--show-current'], { cwd: worktree, encoding: 'utf8', windowsHide: true }).trim();

const task = {
  id: "test-1",
  project: "sargagame",
  repo: "aveca/sargagame",
  payload: {
    description: "test"
  }
};

const child = spawn('node', [
  'C:\\factory\\ai-factory-tmp\\worker-runner.cjs',
  '--task', JSON.stringify(task),
  '--worker-id', 'test-worker',
  '--worktree', worktree,
  '--branch', branch,
  '--model', 'ollama/qwen3-coder:30b',
  '--project', 'sargagame',
  '--repo', 'aveca/sargagame'
], {
  cwd: worktree,
  stdio: 'inherit',
  windowsHide: true,
  env: { ...process.env, HOME: '/home/user' }
});

child.on('close', (code) => {
  console.log(`Worker exited with code ${code}`);
});