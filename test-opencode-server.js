const { spawn } = require('child_process');

// Start server
const server = spawn('opencode', ['serve', '--pure', '--port', '4096'], {
  stdio: ['ignore', 'pipe', 'pipe'],
  windowsHide: true,
  shell: true
});

server.stdout.on('data', d => console.log('SERVER:', d.toString()));
server.stderr.on('data', d => console.log('SERVER ERR:', d.toString()));

// Wait for server to start
setTimeout(() => {
  const prompt = "You are a Factory worker. Task: test-1\nProject: sargagame (aveca/sargagame)\nDescription: test\nWork in the current directory. Make minimal changes. Run tests. Commit and push to your branch.";
  
  const child = spawn('opencode', ['run', '--attach', 'http://127.0.0.1:4096', '--model', 'ollama/qwen3-coder:30b', '--format', 'json', prompt], {
    cwd: 'C:\\factory\\worktrees\\sargagame\\sargagame-1791302731862-jcjhm3',
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
    shell: true,
    env: { ...process.env, HOME: '/home/user' }
  });

  child.stdout.on('data', d => console.log('STDOUT:', d.toString()));
  child.stderr.on('data', d => console.log('STDERR:', d.toString()));
  child.on('close', (code) => {
    console.log(`Client exit code: ${code}`);
    server.kill();
    process.exit(0);
  });
}, 3000);