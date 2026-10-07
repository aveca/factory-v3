console.log('Module path:', require.resolve('./security-validator.cjs'));
const { SecurityValidator } = require('./security-validator.cjs');
const v = new SecurityValidator();
console.log('Testing checkNode:', v.checkNode());
console.log('Testing checkGit:', v.checkGit());
console.log('Testing checkGhCli:', v.checkGhCli());