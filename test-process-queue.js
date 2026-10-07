const { WorkerPool } = require('./worker-pool.cjs');
const p = new WorkerPool();
p.processQueue().then(() => console.log('done')).catch(e => console.error(e));