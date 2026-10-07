const fs = require('fs');
const data = fs.readFileSync('C:\\factory\\events.jsonl', 'utf8');
const lines = data.split('\n').filter(l => l.trim());
// Find lines containing the task ID
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes('1791343040191')) {
    try {
      const e = JSON.parse(lines[i]);
      var msg = '';
      if (e.message) { msg = e.message; if (msg.length > 80) msg = msg.substring(0, 80) + '...'; }
      console.log(i + ':', e.type, '| Task:', (e.task_id || '').substring(0, 30), '| Msg:', msg);
    } catch (e) {
      console.log(i + ': PARSE ERROR');
    }
  }
}