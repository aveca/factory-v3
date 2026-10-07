const { execFileSync } = require('child_process');

const NODE_PATH = 'C:\\Program Files\\nodejs';
const WORKER_ENV = { 
  ...process.env, 
  HOME: '/home/user',
  PATH: NODE_PATH + ';' + (process.env.PATH || '')
};

const checks = [
  { name: 'Node.js', cmd: 'node', args: ['--version'] },
  { name: 'Git', cmd: 'git', args: ['--version'] },
  { name: 'GitHub CLI', cmd: 'gh', args: ['--version'] },
  { name: 'Ollama', cmd: 'ollama', args: ['list'] },
  { name: 'OpenCode', cmd: 'opencode', args: ['--version'] },
];

for (const check of checks) {
  try {
    const output = execFileSync(check.cmd, check.args, { 
      encoding: 'utf8', 
      timeout: 10000, 
      windowsHide: true,
      shell: true,
      env: WORKER_ENV
    });
    console.log(`✓ ${check.name}: ${output.trim()}`);
  } catch (e) {
    console.log(`✗ ${check.name}: ${e.message} (code: ${e.code})`);
  }
}

// Check Gmail auth
const fs = require('fs');
const authFile = 'C:/factory/gmail/auth-state.json';
if (fs.existsSync(authFile)) {
  try {
    const auth = JSON.parse(fs.readFileSync(authFile, 'utf8'));
    console.log(auth.state === 'GMAIL_AUTHENTICATED' ? '✓ Gmail OAuth: OK' : '✗ Gmail OAuth: ' + auth.state);
  } catch (e) {
    console.log('✗ Gmail OAuth: ERROR - ' + e.message);
  }
} else {
  console.log('✗ Gmail OAuth: File not found');
}

// Check GitHub auth
try {
  const output = execFileSync('gh', ['auth', 'status'], { 
    encoding: 'utf8', 
    timeout: 10000, 
    windowsHide: true, 
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: true,
    env: WORKER_ENV
  });
  console.log('✓ GitHub Auth: OK');
} catch (e) {
  console.log('✗ GitHub Auth: ' + e.message);
}