const { execFileSync } = require('child_process');

const WORKER_ENV = { 
  ...process.env, 
  HOME: '/home/user',
  PATH: 'C:\\Program Files\\nodejs;' + (process.env.PATH || '')
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
    console.log(`✗ ${check.name}: ${e.message} (code: ${e.code}, signal: ${e.signal})`);
  }
}