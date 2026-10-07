const { execFileSync } = require('child_process');

const WORKER_ENV = { 
  ...process.env, 
  HOME: '/home/user',
  PATH: 'C:\\Program Files\\nodejs;' + (process.env.PATH || '')
};

console.log('Testing node...');
try {
  const output = execFileSync('node', ['--version'], { 
    encoding: 'utf8', 
    timeout: 5000, 
    windowsHide: true,
    shell: true,
    env: WORKER_ENV
  });
  console.log('✓ Node.js:', output.trim());
} catch (e) {
  console.log('✗ Node.js:', e.message, 'code:', e.code, 'signal:', e.signal, 'errno:', e.errno);
}

console.log('\nTesting git...');
try {
  const output = execFileSync('git', ['--version'], { 
    encoding: 'utf8', 
    timeout: 5000, 
    windowsHide: true,
    shell: true,
    env: WORKER_ENV
  });
  console.log('✓ Git:', output.trim());
} catch (e) {
  console.log('✗ Git:', e.message, 'code:', e.code, 'signal:', e.signal, 'errno:', e.errno);
}

console.log('\nTesting gh...');
try {
  const output = execFileSync('gh', ['--version'], { 
    encoding: 'utf8', 
    timeout: 5000, 
    windowsHide: true,
    shell: true,
    env: WORKER_ENV
  });
  console.log('✓ GitHub CLI:', output.trim());
} catch (e) {
  console.log('✗ GitHub CLI:', e.message, 'code:', e.code, 'signal:', e.signal, 'errno:', e.errno);
}