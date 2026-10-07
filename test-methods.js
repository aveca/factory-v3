const { SecurityValidator } = require('./security-validator.cjs');
const v = new SecurityValidator();

console.log('Testing checkNode directly...');
try {
  const result = v.checkNode();
  console.log('checkNode result:', result);
} catch (e) {
  console.log('checkNode error:', e.message);
}

console.log('\nTesting checkGit directly...');
try {
  const result = v.checkGit();
  console.log('checkGit result:', result);
} catch (e) {
  console.log('checkGit error:', e.message);
}

console.log('\nTesting checkGhCli directly...');
try {
  const result = v.checkGhCli();
  console.log('checkGhCli result:', result);
} catch (e) {
  console.log('checkGhCli error:', e.message);
}