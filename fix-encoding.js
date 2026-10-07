const fs = require('fs');
const content = fs.readFileSync('C:\\factory\\ai-factory-tmp\\worktree-lock.cjs', 'utf8');
// Remove any BOM
const clean = content.replace(/^\uFEFF/, '');
fs.writeFileSync('C:\\factory\\ai-factory-tmp\\worktree-lock-fixed.cjs', clean, 'utf8');
console.log('Written fixed file');