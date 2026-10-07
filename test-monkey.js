const { execFileSync } = require('child_process');

const originalExecFileSync = execFileSync;
global.execFileSync = function(cmd, args, opts) {
  console.log('[DEBUG] execFileSync called:', cmd, args, opts ? Object.keys(opts) : 'no opts');
  try {
    const result = originalExecFileSync.call(this, cmd, args, opts);
    console.log('[DEBUG] execFileSync succeeded:', cmd, args);
    return result;
  } catch (e) {
    console.log('[DEBUG] execFileSync failed:', cmd, args, e.message, 'code:', e.code);
    throw e;
  }
};

delete require.cache[require.resolve('./security-validator.cjs')];
const { SecurityValidator } = require('./security-validator.cjs');
const v = new SecurityValidator();

console.log('Calling checkNode method...');
try {
  const result = v.checkNode();
  console.log('checkNode result:', result);
} catch (e) {
  console.log('checkNode error:', e.message, e.stack);
}