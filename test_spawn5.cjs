const { spawn } = require('child_process');
const path = require('path');

// Fixed __dirname - worker-runner is in ai-factory-tmp
const __dirname = 'C:\\\\factory\\\\ai-factory-tmp';

console.log('process.execPath:', process.execPath);
console.log('__dirname:', __dirname);

// Test: spawn worker-runner.cjs with minimal args
const proc = spawn(process.execPath, [
  path.join(__dirname, 'worker-runner.cjs'),
  '--help'
], {
  cwd: __dirname,
  stdio: ['pipe', 'pipe', 'pipe'],
  windowsHide: true,
  env: process.env
});

proc.stdout.on('data', (data) => {
  console.log('stdout: ' + data.toString().substring(0, 500));
});

proc.stderr.on('data', (data) => {
  console.log('stderr: ' + data.toString().substring(0, 500));
});

proc.on('close', (code) => {
  console.log('Exit code: ' + code);
  process.exit(0);
});

proc.on('error', (err) => {
  console.log('Spawn error: ' + err.code + ' - ' + err.message);
  process.exit(1);
});