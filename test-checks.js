const { execFileSync } = require('child_process');

const checks = [
  { name: 'Node.js', cmd: 'node', args: ['--version'] },
  { name: 'Git', cmd: 'git', args: ['--version'] },
  { name: 'GitHub CLI', cmd: 'gh', args: ['--version'] },
  { name: 'Ollama', cmd: 'ollama', args: ['list'] },
  { name: 'OpenCode', cmd: 'opencode', args: ['--version'] },
  { name: 'GitHub Auth', cmd: 'gh', args: ['auth', 'status'] }
];

for (const check of checks) {
  try {
    const output = execFileSync(check.cmd, check.args, { 
      encoding: 'utf8', 
      timeout: 10000, 
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe']
    });
    console.log(`✓ ${check.name}: ${output.trim()}`);
  } catch (e) {
    console.log(`✗ ${check.name}: ${e.message}`);
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