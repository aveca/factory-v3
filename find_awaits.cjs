const fs = require('fs');
const files = ['worker-runner.cjs', 'worker-pool.cjs'];
files.forEach(f => {
  const data = fs.readFileSync('C:\\\\factory\\\\ai-factory-tmp\\\\' + f, 'utf8');
  const lines = data.split('\n');
  lines.forEach((line, i) => {
    if (line.includes('await')) {
      console.log((i+1) + ': ' + f + ' -> ' + line.trim());
    }
  });
});