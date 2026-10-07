const http = require('http');
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Hello World\n');
});

server.listen(8080, '0.0.0.0', () => {
  console.log('Test server running on http://0.0.0.0:8080/');
});

server.on('error', (e) => {
  console.error('Server error:', e);
});

server.on('listening', () => {
  const address = server.address();
  console.log('Server listening on:', address);
});