const { spawn } = require('child_process');

const child = spawn('opencode', ['--version'], {
  stdio: 'inherit',
  shell: true,
  windowsHide: true
});

child.on('close', (code) => {
  console.log(`Exit code: ${code}`);
});