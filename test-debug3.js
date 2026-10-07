const { execFileSync } = require('child_process');

const WORKER_ENV = { 
  ...process.env, 
  HOME: '/home/user',
  PATH: 'C:\\Program Files\\nodejs;' + (process.env.PATH || '')
};

console.log('Direct execFileSync test...');
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

console.log('\nManually replicating checkNode...');
try {
  const cmd = 'node';
  const args = ['--version'];
  const opts = { 
    encoding: 'utf8', 
    timeout: 5000, 
    windowsHide: true, 
    shell: true, 
    env: v.getWorkerEnv() 
  };
  
  console.log('Options:', JSON.stringify(opts, null, 2));
  
  const out = execFileSync(cmd, args, opts);
  console.log('Manual execFileSync works:', out.trim());
} catch (e) {
  console.log('Manual execFileSync failed:', e.message, 'code:', e.code, 'signal:', e.signal);
}

console.log('\nCalling checkNode method with logging...');
// Monkey patch to see what's happening
const originalCheckNode = v.checkNode;
v.checkNode = function() {
  console.log('[DEBUG] checkNode called, this:', this.constructor.name);
  console.log('[DEBUG] this.getWorkerEnv():', this.getWorkerEnv());
  try {
    const result = execFileSync('node', ['--version'], { 
      encoding: 'utf8', 
      timeout: 5000, 
      windowsHide: true, 
      shell: true, 
      env: this.getWorkerEnv() 
    });
    console.log('[DEBUG] execFileSync succeeded');
    return true;
  } catch (e) {
    console.log('[DEBUG] execFileSync failed:', e.message, 'code:', e.code, 'signal:', e.signal);
    return false;
  }
};

console.log('\nCalling patched checkNode method...');
try {
  const result = v.checkNode();
  console.log('checkNode result:', result);
} catch (e) {
  console.log('checkNode error:', e.message, e.stack);
}