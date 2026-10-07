const http = require('http');
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Hello World\n');
});

server.listen(3456, '127.0.0.1', () => {
  console.log('Test server running on http://127.0.0.1:3456/');
});

server.on('error', (e) => {
  console.error('Server error:', e);
});

server.on('listening', () => {
  const address = server.address();
  console.log('Server listening on:', address);
});