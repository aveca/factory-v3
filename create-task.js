const fs = require('fs');
const path = require('path');
const queueDir = path.resolve('C:/Users/user/sargagame-tmp/queue');

// Ensure queue directory exists
if (!fs.existsSync(queueDir)) {
  console.error('Queue directory not found:', queueDir);
  process.exit(1);
}

const taskId = 'safe-coding-proof-' + Date.now();
const task = {
  id: taskId,
  type: 'coding',
  source: 'factory-proof',
  project: 'ai-factory',
  repo: 'aveca/ai-factory',
  severity: 'P2',
  dedup_key: 'factory|coding-proof',
  evidence: 'factory-coding-proof-real',
  createdAt: new Date().toISOString(),
  timestamp: new Date().toISOString(),
  status: 'new',
  payload: {
    id: taskId,
    source: 'factory-proof',
    repo: 'aveca/ai-factory',
    severity: 'P2',
    error: 'Factory coding proof task - calculateUtil utility'
  },
  retryCount: 0,
  retry_count: 0,
  maxRetries: 3,
  agent: 'coding',
  priority: 2,
  scope: 'factory coding proof',
  acceptance: 'utility function added with test passes',
  allowedFiles: ['**/calculateUtil*', '**/utils/**', '**/test/**'],
  probes: ['ci_logs', 'api'],
  targetFile: 'utils/calculateUtil.js',
  testFile: 'tests/calculateUtil.test.js'
};

const fp = path.join(queueDir, taskId + '.json');
const tmp = fp + '.tmp-' + process.pid;

try {
  fs.writeFileSync(tmp, JSON.stringify(task, null, 2));
  fs.renameSync(tmp, fp);
  console.log('Created: ' + taskId + '.json');
  console.log('Task payload:', JSON.stringify(task.payload, null, 2));
} catch (e) {
  console.error('Create error:', e.message);
  process.exit(1);
}