#!/usr/bin/env node
/** 
 * Test: Run worker-runner on existing queued task 
 * Proves E2E: queue → claim → worker → execution → result 
 */

const path = require('path');
const fs = require('fs');

// Read existing queued task
const q = 'C:/Users/user/sargagame-tmp/queue';
const tasks = fs.readdirSync(q).filter(x => x.endsWith('.json'));
if (tasks.length === 0) {
  console.error('No tasks in queue');
  process.exit(1);
}
const task = JSON.parse(fs.readFileSync(path.join(q, tasks[0]), 'utf8'));

console.log('Using task:', task.id);
console.log('Project:', task.project);
console.log('Repo:', task.repo);

// Create worktree
const worktree = path.resolve('C:\\worktrees\\casinobabe-test');
if (!fs.existsSync(worktree)) {
  fs.mkdirSync(worktree, { recursive: true });
}

// Create branch name
const branch = 'factory/casinobabe-' + Date.now();

// Write task to file for worker-runner
const taskFile = path.join(worktree, 'task.json');
fs.writeFileSync(taskFile, JSON.stringify(task, null, 2));

// Run worker-runner
const { spawn } = require('child_process');
const worker = spawn('node', [
  'C:\\factory\\ai-factory-tmp\\worker-runner.cjs',
  '--task', taskFile,
  '--worktree', worktree,
  '--branch', branch,
  '--model', 'ollama/qwen3-coder:30b',
  '--project', 'casinobabe',
  '--repo', 'aveca/Casinobabe'
], {
  cwd: worktree,
  env: { ...process.env, PATH: 'C:\\\\Program Files\\\\nodejs;' + (process.env.PATH || '') },
  windowsHide: true
});

let stdout = '';
let stderr = '';

worker.stdout.on('data', d => { stdout += d; console.log('WORKER OUT:', d.toString()); });
worker.stderr.on('data', d => { stderr += d; console.log('WORKER ERR:', d.toString()); });
worker.on('close', code => {
  console.log('WORKER EXIT CODE:', code);
  console.log('STDOUT:', stdout.substring(0, 2000));
  console.log('STDERR:', stderr.substring(0, 2000));
  
  // Check if result was persisted
  const resultFile = path.join(worktree, 'result.json');
  if (fs.existsSync(resultFile)) {
    const result = JSON.parse(fs.readFileSync(resultFile, 'utf8'));
    console.log('RESULT:', JSON.stringify(result, null, 2).substring(0, 2000));
  }
  
  // Check session state
  const sessionsDir = path.resolve('C:/factory/sessions');
  if (fs.existsSync(sessionsDir)) {
    const dirs = fs.readdirSync(sessionsDir);
    console.log('Sessions on disk:', dirs);
  }
  
  // Check events stream
  const eventsFile = 'C:/factory/events.jsonl';
  if (fs.existsSync(eventsFile)) {
    const lines = fs.readFileSync(eventsFile, 'utf8').split('\n').filter(l => l.trim());
    console.log('Events stream lines:', lines.length);
    if (lines.length > 0) {
      console.log('Last event:', lines[lines.length - 1].substring(0, 500));
    }
  }
  
  // Check if Core.lua was modified
  const coreFile = path.join(worktree, 'addon', 'CasinoBae', 'Core.lua');
  if (fs.existsSync(coreFile)) {
    const content = fs.readFileSync(coreFile, 'utf8');
    console.log('Core.lua modified:', content.includes('Factory V3 debug logging') ? 'YES' : 'NO');
    console.log('Core.lua last 100 chars:', content.substring(content.length - 100));
  }
  
  process.exit(0);
});