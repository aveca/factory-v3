const { SecurityValidator } = require('./security-validator.cjs');
const v = new SecurityValidator();

console.log('Worker env PATH:', v.getWorkerEnv().PATH);
console.log('Node.js check:', v.checkNode());
console.log('Git check:', v.checkGit());
console.log('GitHub CLI check:', v.checkGhCli());
console.log('Ollama check:', v.checkOllama());
console.log('OpenCode check:', v.checkOpenCode());
console.log('GitHub Auth check:', v.checkGhAuth());
console.log('Gmail Auth check:', v.checkGmailAuth());

console.log('\nFull check:');
console.log(JSON.stringify(v.checkRequiredSecrets(), null, 2));