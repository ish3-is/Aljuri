/**
 * Static server for dist/ that also proxies /api to the backend.
 *
 * The production bundle resolves its API base to a same-origin empty
 * string, so every request goes to /api on this server. Proxying keeps
 * that same-origin, which means the browser applies no CORS rules at
 * all and the test is not constrained to the two origins the backend
 * currently allowlists (localhost:5173 / 127.0.0.1:5173).
 *
 * Used for QA only. It serves the built artefact exactly as shipped.
 */
const http = require('http')
const fs = require('fs')
const path = require('path')

const ROOT = path.join(__dirname, '..', 'dist')
const PORT = Number(process.argv[2] || 5199)
const BACKEND = { host: '127.0.0.1', port: 8000 }

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
  '.otf': 'font/otf',
  '.ttf': 'font/ttf',
  '.map': 'application/json',
}

const server = http.createServer((req, res) => {
  if (req.url.startsWith('/api')) {
    const proxyReq = http.request(
      { ...BACKEND, path: req.url, method: req.method, headers: { ...req.headers, host: `${BACKEND.host}:${BACKEND.port}` } },
      (proxyRes) => {
        res.writeHead(proxyRes.statusCode || 502, proxyRes.headers)
        proxyRes.pipe(res)
      },
    )
    proxyReq.on('error', (e) => {
      res.writeHead(502, { 'content-type': 'application/json' })
      res.end(JSON.stringify({ detail: 'backend unreachable: ' + e.message }))
    })
    req.pipe(proxyReq)
    return
  }

  let filePath = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]))
  if (!filePath.startsWith(ROOT)) {
    res.writeHead(403).end('forbidden')
    return
  }
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.join(ROOT, 'index.html') // SPA fallback
  }
  const ext = path.extname(filePath).toLowerCase()
  res.writeHead(200, { 'content-type': TYPES[ext] || 'application/octet-stream' })
  fs.createReadStream(filePath).pipe(res)
})

server.listen(PORT, '127.0.0.1', () => {
  console.log(`basirah dist on http://localhost:${PORT} (api -> ${BACKEND.host}:${BACKEND.port})`)
})