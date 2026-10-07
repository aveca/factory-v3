const fs = require('fs');
const c = fs.readFileSync('C:\\factory\\ai-factory-tmp\\worktree-lock.cjs', 'utf8');
const lines = c.split('\n');
console.log('Line 202:', lines[201]);
console.log('Char codes:', [...lines[201]].map(c => c.charCodeAt(0)));
console.log('Line 201:', lines[200]);
console.log('Line 203:', lines[202]);