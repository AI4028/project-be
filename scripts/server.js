/**
 * server.js - 배리어프리 키오스크 웹 서버 (Node.js)
 * 모바일 및 로컬 브라우저에서 즉시 접속 가능하도록 frontend 정적 파일 제공
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 8000;
const FRONTEND_DIR = path.join(__dirname, '..', 'frontend');

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.wav': 'audio/wav',
  '.mp3': 'audio/mpeg'
};

const server = http.createServer((req, res) => {
  // CORS 헤더
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', '*');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  let reqPath = req.url.split('?')[0];

  // 루트 or /app 또는 /app/ 접속 시 index.html 서빙
  if (reqPath === '/' || reqPath === '/app' || reqPath === '/app/') {
    reqPath = '/index.html';
  } else if (reqPath.startsWith('/app/')) {
    reqPath = reqPath.replace(/^\/app/, '');
  }

  const filePath = path.join(FRONTEND_DIR, reqPath);

  // 보안 검사: FRONTEND_DIR 내부인지 확인
  if (!filePath.startsWith(FRONTEND_DIR)) {
    res.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('403 Forbidden');
    return;
  }

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      // 헬스체크 지원
      if (reqPath === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok' }));
        return;
      }
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('404 Not Found: ' + reqPath);
      return;
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';

    res.writeHead(200, { 'Content-Type': contentType });
    fs.createReadStream(filePath).pipe(res);
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 키오스크 웹 서버 가동 완료: http://0.0.0.0:${PORT}`);
  console.log(`📱 로컬 Wi-Fi 접속 주소: http://172.17.0.127:${PORT}/app/`);
});
