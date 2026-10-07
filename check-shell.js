const fs = require('fs');
const c = fs.readFileSync('security-validator.cjs', 'utf8');
console.log('Contains shell: true:', c.includes('shell: true'));