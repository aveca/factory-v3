const { execFileSync } = require('child_process');

const WORKER_ENV = { 
  ...process.env, 
  HOME: '/home/user',
  PATH: 'C:\\Program Files\\nodejs;' + (process.env.PATH || '')
};

console.log('Testing SecurityValidator checkNode with full error capture...');
delete require.cache[require.resolve('./security-validator.cjs')];
const { SecurityValidator } = require('./security-validator.cjs');
const v = new SecurityValidator();

console.log('Worker env PATH:', v.getWorkerEnv().PATH);

console.log('\nManually calling execFileSync inside the class context...');
try {
  const out = execFileSync('node', ['--version'], { 
    cwd: process.cwd(),
    encoding: 'utf8', 
    timeout: 5000, 
    windowsHide: true, 
    shell: true, 
    env: v.getWorkerEnv() 
  });
  console.log('Direct execFileSync with class env works:', out.trim());
} catch (e) {
  console.log('Direct execFileSync with class env failed:', e.message, 'code:', e.code, 'signal:', e.signal, 'errno:', e.errno);
}

console.log('\nCalling checkNode method with full error capture...');
try {
  // Manually replicate what checkNode does
  const cmd = 'node';
  const args = ['--version'];
  const opts = { 
    cwd: process.cwd(),
    encoding: 'utf8', 
    timeout: 5000, 
    windowsHide: true, 
    shell: true, 
    env: v.getWorkerEnv() 
  };
  
  const out = execFileSync(cmd, args, opts);
  console.log('Manual execFileSync works:', out.trim());
} catch (e) {
  console.log('Manual execFileSync failed:', e.message, 'code:', e.code, 'signal:', e.signal, 'errno:', e.errno);
}

console.log('\nCalling checkNode method with full error capture...');
try {
  const result = v.checkNode();
  console.log('checkNode result:', result);
} catch (e) {
  console.log('checkNode error:', e.message, e.stack);
}