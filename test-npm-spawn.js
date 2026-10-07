const { spawn } = require('child_process');

const WORKER_ENV = { 
  ...process.env, 
  HOME: '/home/user',
  PATH: 'C:\\Program Files\\nodejs;' + (process.env.PATH || '')
};

const child = spawn('npm.cmd', ['test'], {
  cwd: 'C:\\factory\\worktrees\\sargagame\\sargagame-1791302731862-jcjhm3',
  stdio: ['ignore', 'pipe', 'pipe'],
  windowsHide: true,
  shell: true,
  env: WORKER_ENV
});

child.stdout.on('data', d => console.log('STDOUT:', d.toString()));
child.stderr.on('data', d => console.log('STDERR:', d.toString()));
child.on('close', (code) => console.log(`Exit code: ${code}`));
child.on('error', (e) => console.log('ERROR:', e.message));