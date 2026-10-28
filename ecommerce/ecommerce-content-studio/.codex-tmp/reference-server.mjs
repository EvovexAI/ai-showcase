import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'

const port = Number(process.env.REFERENCE_PORT || 8790)
const files = process.argv.slice(2).map(file => path.resolve(file))

if (!files.length || files.some(file => !fs.existsSync(file))) {
  console.error('Reference files are missing')
  process.exit(1)
}

const server = http.createServer((req, res) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.writeHead(405).end()
    return
  }
  if (req.url === '/health') {
    res.writeHead(200, { 'content-type': 'text/plain', 'cache-control': 'no-store' })
    res.end('ok')
    return
  }
  const match = req.url?.match(/^\/reference-(\d+)\.jpg$/)
  const index = match ? Number(match[1]) - 1 : -1
  if (index < 0 || index >= files.length) {
    res.writeHead(404, { 'content-type': 'text/plain', 'cache-control': 'no-store' })
    res.end('not found')
    return
  }
  const stat = fs.statSync(files[index])
  res.writeHead(200, {
    'content-type': 'image/jpeg',
    'content-length': stat.size,
    'cache-control': 'no-store, max-age=0',
    'x-content-type-options': 'nosniff'
  })
  if (req.method === 'HEAD') {
    res.end()
    return
  }
  fs.createReadStream(files[index]).pipe(res)
})

server.listen(port, '127.0.0.1', () => {
  console.log(`Reference server listening on http://127.0.0.1:${port}`)
})
