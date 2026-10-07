const fs = require('fs');
const content = fs.readFileSync('C:\\factory\\ai-factory-tmp\\worktree-lock.cjs', 'utf8');
const lines = content.split('\n');

// Check the exact structure around the heartbeat function
for (let i = 190; i < 210; i++) {
  console.log(`${i+1}: ${lines[i]}`);
}

// Also check for unclosed braces in the whole file
let braceCount = 0;
for (let i = 0; i < content.length; i++) {
  if (content[i] === '{') braceCount++;
  if (content[i] === '}') braceCount--;
}
console.log('Total brace balance:', braceCount);