const { SecurityValidator } = require('./security-validator.cjs');
const v = new SecurityValidator();

console.log('Testing checkNode with detailed error...');
try {
  const result = v.checkNode();
  console.log('checkNode result:', result);
} catch (e) {
  console.log('checkNode error:', e.message, e.stack);
}

console.log('\nTesting checkGit with detailed error...');
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