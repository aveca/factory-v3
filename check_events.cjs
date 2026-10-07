const fs = require('fs');
const data = fs.readFileSync('C:\\factory\\events.jsonl', 'utf8');
const lines = data.split('\n').filter(l => l.trim());
let count = 0;
for (const l of lines) {
  try {
    const e = JSON.parse(l);
    if (e.type === 'TASK_CLAIMED' || e.type === 'WORKER_STARTED' || e.type === 'FAILED') {
      count++;
    }
  } catch {}
}
console.log('Relevant events:', count, 'of', lines.length, 'total lines');