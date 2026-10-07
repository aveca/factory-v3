const fs = require('fs');
const data = fs.readFileSync('C:\\\\factory\\\\ai-factory-tmp\\\\worker-runner.cjs', 'utf8');
const lines = data.split('\n');
lines.forEach((line, i) => {
  const trimmed = line.trim();
  if (/async function|function |^const main|^main =/.test(trim)) {
    console.log((i+1) + ': ' + trimmed);
  }
});