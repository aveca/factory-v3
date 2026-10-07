const fs = require('fs');
const path = require('path');
const { SessionManager } = require('./session-manager.cjs');
const { WorkerPool } = require('./worker-pool.cjs');

async function runCrashRecoveryTest() {
  console.log('\n=== FORCED CRASH RECOVERY TEST ===\n');
  
  // Create a task that will force failure
  const taskId = `crash-recovery-test-${Date.now()}`;
  const taskFile = path.join('C:/Users/user/sargagame-tmp/queue', taskId + '.json');
  const task = {
    id: taskId,
    project: 'casinobabe',
    repo: 'aveca/Casinobabe',
    source: 'crash-recovery-test',
    severity: 'low',
    status: 'new',
    payload: {
      description: 'CRASH RECOVERY TEST: Force worker crash',
      requirements: ['Modify addon/CasinoBae/Core.lua', 'Run Lua validation', 'Commit and push'],
      forceFailure: true  // This will cause the worker to crash
    },
    createdAt: new Date().toISOString()
  };
  
  fs.writeFileSync(taskFile, JSON.stringify(task, null, 2));
  console.log(`Created task: ${taskId}`);
  
  const sessionManager = new (require('./session-manager.cjs').SessionManager)();
  const workerPool = new WorkerPool();
  
  workerPool.running = true;
  workerPool.startWatchdog();
  
  // Process the queue - should start a worker
  await workerPool.processQueue();
  
  console.log('\nWorker started. Waiting for it to crash...');
  
  // Wait for worker to crash
  let crashed = false;
  const checkInterval = setInterval(() => {
    const status = workerPool.getStatus();
    if (status.activeWorkers === 0 && workerPool.workers.size > 0) {
      const worker = Array.from(workerPool.workers.values())[0];
      if (worker.status === 'failed' || worker.status === 'crashed') {
        console.log(`\nWorker ${worker.worker_id} crashed! Watchdog should trigger recovery...`);
        crashed = true;
        clearInterval(checkInterval);
      }
    }
    
    if (crashed) {
      clearInterval(checkInterval);
      console.log('\nWaiting for recovery worker to start...');
      
      // Wait for recovery
      const recoveryInterval = setInterval(() => {
        const status = workerPool.getStatus();
        if (status.activeWorkers > 0) {
          const newWorker = Array.from(workerPool.workers.values()).find(w => w.status === 'running');
          if (newWorker) {
            console.log(`Recovery worker ${newWorker.worker_id} started for session ${newWorker.sessionId}`);
            clearInterval(recoveryInterval);
            console.log('\n=== RECOVERY TEST PASSED ===');
            console.log('Watchdog detected crash and spawned recovery worker');
            process.exit(0);
          }
        }
      }, 5000);
      
      // Timeout after 2 minutes
      setTimeout(() => {
        clearInterval(recoveryInterval);
        console.log('\nTimeout waiting for recovery');
        process.exit(1);
      }, 120000);
    }
  }, 5000);
  
  // Timeout for initial crash
  setTimeout(() => {
    if (!crashed) {
      clearInterval(checkInterval);
      console.log('\nTimeout waiting for worker to crash');
      process.exit(1);
    }
  }, 180000);
  
  // Process the queue to start the worker
  await workerPool.processQueue();
}

runCrashRecoveryTest().catch(e => { console.error(e); process.exit(1); });