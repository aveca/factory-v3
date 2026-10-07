const fs = require('fs');
const c = fs.readFileSync('security-validator.cjs', 'utf8');
console.log('Has shell: true:', c.includes('shell: true'));
console.log('Has getWorkerEnv:', c.includes('getWorkerEnv'));