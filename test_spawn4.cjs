const { spawn } = require('child_process');

console.log('process.execPath:', process.execPath);
console.log('__dirname:', __dirname);
console.log('process.cwd():', process.cwd());

// Simplest possible spawn test
const proc = spawn(process.execPath, ['-e', 'console.log("hello from spawned node")'], {
  cwd: 'C:\\\\factory',
  stdio: ['pipe', 'pipe', 'pipe'],
  windowsHide: true,
  env: process.env
});

proc.stdout.on('data', (data) => {
  console.log('stdout: ' + data.toString());
});

proc.stderr.on('data', (data) => {
  console.log('stderr: ' + data.toString());
});

proc.on('close', (code) => {
  console.log('Exit code: ' + code);
  process.exit(0);
});

proc.on('error', (err) => {
  console.log('Spawn error: ' + err.code + ' - ' + err.message);
  process.exit(1);
});