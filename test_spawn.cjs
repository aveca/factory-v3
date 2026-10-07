const { spawn } = require('child_process');
const path = require('path');

// Replicate the exact spawn from worker-pool.cjs line 224-246
const task = {
  id: 'test-task-' + Date.now(),
  project: 'sargagame',
  repo: 'aveca/sargagame',
  source: 'factory_test',
  severity: 'info',
  status: 'NEW',
  payload: {
    description: 'Quick fix test',
    requirements: ['test']
  },
  createdAt: new Date().toISOString()
};

// Get the actual __dirname
const __dirname = 'C:\\\\factory\\\\ai-factory-tmp';

const workerId = 'test-worker-1';
const worktreePath = 'C:\\\\factory\\\\worktrees\\\\sargagame\\\\test-' + Date.now();

try {
  const workerProc = spawn('node', [
    path.join(__dirname, 'worker-runner.cjs'),
    '--task', JSON.stringify(task),
    '--worker-id', workerId,
    '--worktree', worktreePath,
    '--branch', 'factory/test-' + Date.now(),
    '--model', 'ollama/qwen2.5-coder:7b',
    '--project', 'sargagame',
    '--repo', 'aveca/sargagame',
    '--session-id', 'test-session-' + Date.now()
  ], {
    cwd: worktreePath,
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
    env: { 
      ...process.env, 
      HOME: '/home/user',
      FACTORY_WORKER_ID: workerId,
      FACTORY_TASK_ID: task.id,
      FACTORY_SESSION_ID: 'test-session-' + Date.now(),
      FACTORY_EVENT_STREAM: 'C:\\\\factory\\\\events.jsonl'
    }
  });

  workerProc.on('close', (code) => {
    console.log('Exit code: ' + code);
    process.exit(0);
  });

  workerProc.on('error', (err) => {
    console.log('Spawn error: ' + err.code + ' - ' + err.message);
    process.exit(1);
  });

  // Kill after 10 seconds if still running
  setTimeout(() => {
    console.log('Timeout - killing worker');
    workerProc.kill('SIGKILL');
    process.exit(1);
  }, 10000);

} catch(e) {
  console.log('Error: ' + e.message);
  process.exit(1);
}