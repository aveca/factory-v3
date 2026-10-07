const { execFileSync } = require('child_process');

console.log('execFileSync function:', typeof execFileSync);
console.log('execFileSync name:', execFileSync.name);

const WORKER_ENV = { 
  ...process.env, 
  HOME: '/home/user',
  PATH: 'C:\\Program Files\\nodejs;' + (process.env.PATH || '')
};

console.log('\nTesting execFileSync directly...');
try {
  const out = execFileSync('node', ['--version'], { 
    encoding: 'utf8', 
    timeout: 5000, 
    windowsHide: true, 
    shell: true, 
    env: WORKER_ENV 
  });
  console.log('Direct execFileSync works:', out.trim());
} catch (e) {
  console.log('Direct execFileSync failed:', e.message, 'code:', e.code);
}

delete require.cache[require.resolve('./security-validator.cjs')];
const { SecurityValidator } = require('./security-validator.cjs');
const v = new SecurityValidator();

console.log('\nCalling checkNode method...');
try {
  const result = v.checkNode();
  console.log('checkNode result:', result);
} catch (e) {
  console.log('checkNode error:', e.message, e.stack);
}