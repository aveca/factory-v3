const { spawn } = require('child_process');

const task = {
  id: "recovery-test-1791311403447",
  project: "casinobabe",
  repo: "aveca/Casinobabe",
  payload: {
    description: "RECOVERY TEST: Add debug logging to Core.lua",
    requirements: [
      "Modify addon/CasinoBae/Core.lua",
      "Run Lua validation",
      "Commit and push"
    ]
  }
};

const worktree = 'C:\\factory\\worktrees\\casinobabe\\casinobabe-1791312320816-jf5s92';
const branch = 'factory/casinobabe-1791312320816-abc123';
const model = 'ollama/qwen3-coder:30b';
const project = 'casinobabe';
const repo = 'aveca/Casinobabe';
const sessionId = 'test-session-123';
const workerId = 'test-worker-1';

const child = spawn('node', [
  'C:\\factory\\ai-factory-tmp\\worker-runner.cjs',
  '--task', JSON.stringify(task),
  '--worktree', worktree,
  '--branch', branch,
  '--model', model,
  '--project', project,
  '--repo', repo,
  '--session-id', sessionId,
  '--worker-id', workerId
], {
  cwd: worktree,
  stdio: ['ignore', 'pipe', 'pipe'],
  windowsHide: true,
  env: { 
    ...process.env, 
    HOME: '/home/user',
    FACTORY_WORKER_ID: workerId,
    FACTORY_TASK_ID: 'recovery-test-1791311403447',
    FACTORY_SESSION_ID: sessionId,
    FACTORY_EVENT_STREAM: 'C:/factory/events.jsonl'
  }
});

child.stdout.on('data', d => console.log('STDOUT:', d.toString()));
child.stderr.on('data', d => console.log('STDERR:', d.toString()));
child.on('close', (code) => console.log(`Exit code: ${code}`));
child.on('error', (e) => console.log('ERROR:', e.message));