const { spawn } = require('child_process');

const prompt = "You are a Factory worker. Task: test-1\nProject: sargagame (aveca/sargagame)\nDescription: test\nSargagame is a React/Preact/Vite beach monitoring app. Use npm test for tests.\nWork in the current directory. Make minimal changes. Run tests. Commit and push to your branch.";

const child = spawn('opencode', ['run', '--pure', '--model', 'ollama/qwen3-coder:30b', '--format', 'json', prompt], {
  cwd: 'C:\\factory\\worktrees\\sargagame\\sargagame-1791302731862-jcjhm3',
  stdio: ['ignore', 'pipe', 'pipe'],
  windowsHide: true,
  shell: true,
  env: { ...process.env, HOME: '/home/user' }
});

child.stdout.on('data', d => console.log('STDOUT:', d.toString()));
child.stderr.on('data', d => console.log('STDERR:', d.toString()));
child.on('close', (code) => console.log(`Exit code: ${code}`));