const fs = require('fs');
const content = fs.readFileSync('C:\\factory\\ai-factory-tmp\\worktree-lock.cjs', 'utf8');
const lines = content.split('\n');

let braceCount = 0;
for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  for (let j = 0; j < line.length; j++) {
    if (line[j] === '{') braceCount++;
    if (line[j] === '}') braceCount--;
  }
  if (braceCount !== 0) {
    console.log(`${i+1} (balance: ${braceCount}): ${lines[i]}`);
  }
}
console.log('Final balance:', braceCount);