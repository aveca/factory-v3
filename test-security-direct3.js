delete require.cache[require.resolve('./security-validator.cjs')];
const { SecurityValidator } = require('./security-validator.cjs');
const v = new SecurityValidator();
console.log('Worker env PATH:', v.getWorkerEnv().PATH);

console.log('\nTesting checkNode directly...');
try {
  const result = v.checkNode();
  console.log('checkNode result:', result);
} catch (e) {
  console.log('checkNode error:', e.message, e.stack);
}

console.log('\nTesting checkGit directly...');
try {
  const result = v.checkGit();
  console.log('checkGit result:', result);
} catch (e) {
  console.log('checkGit error:', e.message, e.stack);
}

console.log('\nTesting checkGhCli directly...');
try {
  const result = v.checkGhCli();
  console.log('checkGhCli result:', result);
} catch (e) {
  console.log('checkGhCli error:', e.message, e.stack);
}

console.log('\nFull check:');
console.log(JSON.stringify(v.checkRequiredSecrets(), null, 2));