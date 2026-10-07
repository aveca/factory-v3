const fs = require('fs');
const data = fs.readFileSync('C:\\factory\\events.jsonl', 'utf8');
const lines = data.split('\n').filter(l => l.trim());
console.log('Total event lines:', lines.length);
for (let i = Math.max(0, lines.length - 5); i < lines.length; i++) {
  try {
    const e = JSON.parse(lines[i]);
    var msg = '';
    if (e.message) { msg = e.message; if (msg.length > 60) msg = msg.substring(0, 60) + '...'; }
    console.log(i + ':', e.type, '|', (e.task_id || '').substring(0, 20), '|', msg);
  } catch {
    console.log(i + ': PARSE ERROR');
  }
}