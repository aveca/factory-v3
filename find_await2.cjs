const fs = require('fs');
const files = [
  'agent-executor-interface.cjs',
  'agent-executor-interface.cjs'
];
files.forEach(f => {
  try {
    const data = fs.readFileSync('C:\\\\factory\\\\ai-factory-tmp\\\\' + f, 'utf8');
    const lines = data.split('\n');
    lines.forEach((line, i) => {
      if (line.includes('await')) {
        console.log((i+1) + ': ' + f + ' -> ' + line.trim());
      }
    });
  } catch(e) { console.log(f + ': ERROR - ' + e.message.substring(0, 40)); }
});