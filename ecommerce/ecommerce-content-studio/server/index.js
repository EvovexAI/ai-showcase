import express from 'express'
import multer from 'multer'
import path from 'node:path'
import fs from 'node:fs'
import crypto from 'node:crypto'
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { fileURLToPath } from 'node:url'

const execFileAsync = promisify(execFile)
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const dataDir = path.join(root, 'data')
const uploadDir = path.join(root, 'uploads')
const outputDir = path.join(root, 'generated')
const dbFile = path.join(dataDir, 'db.json')
for (const dir of [dataDir, uploadDir, outputDir]) fs.mkdirSync(dir, { recursive: true })

const platforms = [
  { id: 'taobao', name: '淘宝/天猫', accent: '#ff6a33', main: '1:1 · 800×800', detail: '750px 宽', rules: ['首图简洁突出主体', '详情页移动端优先', '价格与功效表述需可证明'] },
  { id: 'douyin', name: '抖音电商', accent: '#2dd4bf', main: '1:1 · 1200×1200', detail: '750px 宽', rules: ['前三秒展示核心利益点', '强调短视频原生感', '避免极限词与承诺性表述'] },
  { id: 'jd', name: '京东', accent: '#ef4444', main: '1:1 · 800×800', detail: '790px 宽', rules: ['白底主图主体占比高', '参数信息清晰', '突出品质与履约信任'] },
  { id: 'pdd', name: '拼多多', accent: '#f43f5e', main: '1:1 · 800×800', detail: '750px 宽', rules: ['卖点直给、易扫读', '突出规格组合', '促销信息避免误导'] },
  { id: 'amazon', name: 'Amazon', accent: '#f59e0b', main: '1:1 · 2000×2000', detail: '1464×600', rules: ['主图纯白背景', '主体占画面 85% 左右', 'A+ 页面重视场景和对比'] },
  { id: 'shopify', name: 'Shopify 独立站', accent: '#8b5cf6', main: '4:5 · 1600×2000', detail: '1440px 宽', rules: ['品牌视觉一致', '生活方式场景优先', '适合多语言本地化'] }
]

const initialDb = {
  projects: [],
  settings: {
    reasoning: { provider: 'openai-compatible', endpoint: '', model: '', apiKey: '' },
    search: { provider: 'bing-public', endpoint: '' },
    assetPublicBaseUrl: '',
    defaults: { imageModel: '', videoModel: '', language: 'zh-CN' }
  },
  quotes: []
}

function readDb() {
  if (!fs.existsSync(dbFile)) fs.writeFileSync(dbFile, JSON.stringify(initialDb, null, 2))
  try { return JSON.parse(fs.readFileSync(dbFile, 'utf8')) } catch { return structuredClone(initialDb) }
}
function writeDb(db) {
  const temp = `${dbFile}.tmp`
  fs.writeFileSync(temp, JSON.stringify(db, null, 2))
  fs.renameSync(temp, dbFile)
}
function id(prefix = 'id') { return `${prefix}_${Date.now().toString(36)}_${crypto.randomBytes(3).toString('hex')}` }
function cleanName(name) { return String(name || 'asset').replace(/[^\p{L}\p{N}._-]+/gu, '-').slice(0, 80) }
function projectOr404(db, projectId, res) {
  const project = db.projects.find(p => p.id === projectId)
  if (!project) res.status(404).json({ error: '找不到这个商品项目' })
  return project
}

async function runBoli(args, timeout = 120000) {
  try {
    let command = 'boli'
    let commandArgs = args
    if (process.platform === 'win32') {
      const searchDirs = [...new Set([
        ...(process.env.PATH || '').split(path.delimiter),
        process.env.APPDATA ? path.join(process.env.APPDATA, 'AILauncher', 'node') : ''
      ].filter(Boolean))]
      const entry = searchDirs.map(dir => path.join(dir, 'node_modules', '@boli-ai', 'cli', 'dist', 'index.js')).find(file => fs.existsSync(file))
      if (!entry) throw new Error('未找到 BOLI CLI 运行入口，请确认已安装且位于 PATH 中')
      command = process.execPath
      commandArgs = [entry, ...args]
    }
    const { stdout } = await execFileAsync(command, commandArgs, { timeout, maxBuffer: 10 * 1024 * 1024, windowsHide: true })
    const lines = stdout.trim().split(/\r?\n/).filter(Boolean)
    for (let i = lines.length - 1; i >= 0; i--) {
      try { return JSON.parse(lines[i]) } catch {}
    }
    throw new Error('BOLI 未返回可解析的 JSON')
  } catch (error) {
    const combined = [error.stdout, error.stderr].filter(Boolean).join('\n')
    const lines = combined.trim().split(/\r?\n/).filter(Boolean)
    for (let i = lines.length - 1; i >= 0; i--) {
      try {
        const parsed = JSON.parse(lines[i])
        const message = parsed?.error?.message || parsed?.error || parsed?.message
        if (message) throw new Error(String(message).slice(0, 1200))
      } catch (parseError) {
        if (parseError instanceof SyntaxError) continue
        throw parseError
      }
    }
    const message = combined || error.message
    throw new Error(String(message).slice(0, 1200))
  }
}

async function listModels(type) {
  const result = await runBoli(['models', 'list', '--type', type, '--json'])
  return result.data || []
}

function optionArgs(options, allowed) {
  const args = []
  for (const [key, flag] of Object.entries(allowed)) {
    if (options[key] !== undefined && options[key] !== '' && options[key] !== null) args.push(flag, String(options[key]))
  }
  return args
}

const forbiddenLexicon = [
  ['国家级', '资质/级别绝对化'], ['最高级', '极限词'], ['最佳', '极限词'], ['第一', '排名缺少证据'], ['顶级', '极限词'],
  ['100%', '绝对承诺'], ['永久', '时效绝对化'], ['绝对', '绝对化表述'], ['治愈', '医疗功效'], ['根治', '医疗功效'],
  ['零风险', '风险承诺'], ['无副作用', '医疗/安全绝对化'], ['全网最低', '价格极限词'], ['万能', '夸大功效']
]
function complianceScan(text = '') {
  const hits = []
  for (const [word, reason] of forbiddenLexicon) {
    let index = text.indexOf(word)
    while (index >= 0) { hits.push({ word, reason, index, severity: reason.includes('医疗') ? 'high' : 'medium' }); index = text.indexOf(word, index + word.length) }
  }
  return { score: Math.max(0, 100 - hits.length * 12), hits, scannedAt: new Date().toISOString(), scope: '内置规则库初筛；发布前仍需按平台最新规则复核' }
}

function isPublicHttpUrl(value) {
  try {
    const parsed = new URL(value)
    if (!['http:', 'https:'].includes(parsed.protocol)) return false
    const host = parsed.hostname.toLowerCase()
    if (host === 'localhost' || host === '::1' || host.endsWith('.local') || /^127\./.test(host) || /^10\./.test(host) || /^192\.168\./.test(host)) return false
    const match = host.match(/^172\.(\d+)\./)
    if (match && Number(match[1]) >= 16 && Number(match[1]) <= 31) return false
    return true
  } catch { return false }
}

async function publicSearch(query) {
  const url = `https://www.bing.com/search?q=${encodeURIComponent(query)}&setlang=zh-hans`
  const response = await fetch(url, { headers: { 'user-agent': 'Mozilla/5.0 CommerceResearchBot/1.0' }, signal: AbortSignal.timeout(15000) })
  if (!response.ok) throw new Error(`联网检索失败：${response.status}`)
  const html = await response.text()
  const results = []
  const blocks = [...html.matchAll(/<li class="b_algo"[\s\S]*?<h2[^>]*><a[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>[\s\S]*?<p[^>]*>([\s\S]*?)<\/p>/gi)].slice(0, 8)
  const strip = value => value.replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&#39;/g, "'").replace(/&quot;/g, '"').trim()
  for (const match of blocks) results.push({ url: match[1], title: strip(match[2]), snippet: strip(match[3]) })
  return results
}

function heuristicInsight(project, sources) {
  const category = project.category || '消费品'
  const sourceText = sources.map(s => `${s.title} ${s.snippet}`).join(' ')
  const frequent = ['便携', '耐用', '易清洁', '颜值', '收纳', '效率', '安全', '性价比'].filter(w => sourceText.includes(w))
  const selling = [...new Set([...frequent, '真实材质与细节可视化', '使用前后场景对照', '规格与适配边界说清楚'])].slice(0, 5)
  return {
    summary: `围绕“${project.name}”完成公开网页初步扫描。${category}用户通常先看使用场景与核心收益，再比较材质、规格、维护成本与可信证据。`,
    personas: [
      { name: '效率导向用户', need: '快速判断是否适合自己的场景', concern: '功能是否夸大、使用是否复杂' },
      { name: '品质导向用户', need: '材质、工艺和细节证据', concern: '实物与图片是否一致' },
      { name: '价格敏感用户', need: '规格组合与长期使用价值', concern: '隐性成本和售后' }
    ],
    painPoints: ['信息很多但看不出实际解决什么问题', '缺少尺寸、材质和适配范围的直观参照', '担心效果图与真实商品不一致', '不知道如何使用、清洁或维护'],
    sellingPoints: selling,
    creativeDirections: [
      { title: '一眼看懂', detail: '首图只保留商品、核心利益点和一处可信证据' },
      { title: '场景证明', detail: '用真实环境展示使用动作、尺寸和前后差异' },
      { title: '细节消疑', detail: '用微距、拆解或标注呈现材质与关键结构' }
    ],
    keywords: [...new Set([project.name, category, ...frequent, '测评', '使用方法', '怎么选'])].slice(0, 10),
    sourceCount: sources.length,
    sources,
    generatedAt: new Date().toISOString()
  }
}

async function callReasoning(settings, project, sources) {
  const { endpoint, model, apiKey } = settings.reasoning || {}
  if (!endpoint || !model || !apiKey) return heuristicInsight(project, sources)
  const response = await fetch(`${endpoint.replace(/\/$/, '')}/chat/completions`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({ model, temperature: 0.35, response_format: { type: 'json_object' }, messages: [
      { role: 'system', content: '你是电商市场洞察专家。基于检索证据输出 JSON，字段必须包括 summary, personas, painPoints, sellingPoints, creativeDirections, keywords。不要编造具体销量或排名。' },
      { role: 'user', content: JSON.stringify({ product: { name: project.name, category: project.category, description: project.description, platform: project.platform }, sources }) }
    ] }),
    signal: AbortSignal.timeout(60000)
  })
  if (!response.ok) throw new Error(`推理模型调用失败：${response.status}`)
  const payload = await response.json()
  const content = payload.choices?.[0]?.message?.content || '{}'
  return { ...JSON.parse(content.replace(/^```json\s*|```$/g, '')), sources, sourceCount: sources.length, generatedAt: new Date().toISOString() }
}

const app = express()
app.use(express.json({ limit: '5mb' }))
app.use('/uploads', express.static(uploadDir))
app.use('/generated', express.static(outputDir))

const storage = multer.diskStorage({
  destination: uploadDir,
  filename: (_req, file, cb) => cb(null, `${Date.now()}-${crypto.randomBytes(3).toString('hex')}-${cleanName(file.originalname)}`)
})
const upload = multer({ storage, limits: { fileSize: 200 * 1024 * 1024, files: 20 }, fileFilter: (_req, file, cb) => {
  const ok = /^(image|video)\//.test(file.mimetype)
  cb(ok ? null : new Error('仅支持图片或视频素材'), ok)
} })

app.get('/api/health', async (_req, res) => {
  try {
    const [auth, capabilities, balance] = await Promise.all([runBoli(['auth', 'status', '--json']), runBoli(['capabilities', '--json']), runBoli(['balance', '--json'])])
    res.json({ ok: true, boli: { authenticated: auth.ok, scopes: auth.scopes, operations: capabilities.operations, balance: balance.balance, currency: balance.currency } })
  } catch (error) { res.status(503).json({ ok: false, error: error.message }) }
})
app.get('/api/platforms', (_req, res) => res.json(platforms))
app.get('/api/projects', (_req, res) => res.json(readDb().projects))
app.post('/api/projects', (req, res) => {
  const db = readDb()
  const now = new Date().toISOString()
  const project = {
    id: id('prd'), name: req.body.name?.trim() || '未命名商品', category: req.body.category?.trim() || '其他',
    description: req.body.description?.trim() || '', platform: req.body.platform || 'taobao', language: req.body.language || 'zh-CN',
    status: 'draft', progress: 8, createdAt: now, updatedAt: now, assets: [], outputs: [], jobs: [], insight: null,
    brief: { mainCount: 5, skuCount: 6, detailCount: 8, ratios: ['1:1', '3:4', '9:16'], videoTypes: ['主图视频', '操作视频', '营销视频'] }
  }
  db.projects.unshift(project); writeDb(db); res.status(201).json(project)
})
app.get('/api/projects/:id', (req, res) => {
  const db = readDb(); const project = projectOr404(db, req.params.id, res); if (project) res.json(project)
})
app.patch('/api/projects/:id', (req, res) => {
  const db = readDb(); const project = projectOr404(db, req.params.id, res); if (!project) return
  const allowed = ['name', 'category', 'description', 'platform', 'language', 'status', 'brief']
  for (const key of allowed) if (req.body[key] !== undefined) project[key] = req.body[key]
  project.updatedAt = new Date().toISOString(); writeDb(db); res.json(project)
})
app.delete('/api/projects/:id', (req, res) => {
  const db = readDb(); const index = db.projects.findIndex(p => p.id === req.params.id)
  if (index < 0) return res.status(404).json({ error: '项目不存在' })
  db.projects.splice(index, 1); writeDb(db); res.status(204).end()
})
app.post('/api/projects/:id/assets', upload.array('files', 20), (req, res) => {
  const db = readDb(); const project = projectOr404(db, req.params.id, res); if (!project) return
  const kind = req.body.kind || 'product'
  const added = (req.files || []).map(file => ({ id: id('ast'), name: file.originalname, kind, source: 'local', mime: file.mimetype, size: file.size, url: `/uploads/${file.filename}`, createdAt: new Date().toISOString() }))
  project.assets.push(...added); project.updatedAt = new Date().toISOString(); project.progress = Math.max(project.progress, 20); writeDb(db); res.status(201).json(added)
})
app.post('/api/projects/:id/assets/url', (req, res) => {
  const db = readDb(); const project = projectOr404(db, req.params.id, res); if (!project) return
  try { new URL(req.body.url) } catch { return res.status(400).json({ error: '请输入有效的 http(s) 素材地址' }) }
  const asset = { id: id('ast'), name: req.body.name || '外部参考素材', kind: req.body.kind || 'product', source: 'url', mime: req.body.mime || 'image/*', size: 0, url: req.body.url, createdAt: new Date().toISOString() }
  project.assets.push(asset); project.updatedAt = new Date().toISOString(); writeDb(db); res.status(201).json(asset)
})
app.delete('/api/projects/:projectId/assets/:assetId', (req, res) => {
  const db = readDb(); const project = projectOr404(db, req.params.projectId, res); if (!project) return
  const asset = project.assets.find(a => a.id === req.params.assetId)
  project.assets = project.assets.filter(a => a.id !== req.params.assetId); writeDb(db)
  if (asset?.source === 'local') { const full = path.join(root, asset.url); if (full.startsWith(uploadDir) && fs.existsSync(full)) fs.unlinkSync(full) }
  res.status(204).end()
})
app.patch('/api/projects/:projectId/assets/:assetId', (req, res) => {
  const db = readDb(); const project = projectOr404(db, req.params.projectId, res); if (!project) return
  const asset = project.assets.find(item => item.id === req.params.assetId)
  if (!asset) return res.status(404).json({ error: '素材不存在' })
  const allowedKinds = new Set(['front', 'top', 'side', 'product', 'scene', 'prop', 'person', 'footage'])
  if (req.body.kind && allowedKinds.has(req.body.kind)) asset.kind = req.body.kind
  if (req.body.name?.trim()) asset.name = req.body.name.trim().slice(0, 120)
  project.updatedAt = new Date().toISOString(); writeDb(db); res.json(asset)
})
app.post('/api/projects/:id/outputs/import', (req, res) => {
  const db = readDb(); const project = projectOr404(db, req.params.id, res); if (!project) return
  const url = String(req.body.url || '')
  if (!url.startsWith('/generated/') && !/^https?:\/\//i.test(url)) return res.status(400).json({ error: '成果地址必须来自 generated 目录或有效公网 URL' })
  const output = { id: id('out'), kind: req.body.kind === 'video' ? 'video' : 'image', name: req.body.name || '导入成果', url, createdAt: new Date().toISOString(), meta: req.body.meta || {} }
  project.outputs.push(output); project.progress = Math.max(project.progress, output.kind === 'image' ? 62 : 78); project.updatedAt = new Date().toISOString(); writeDb(db); res.status(201).json(output)
})
app.post('/api/projects/:id/analyze', async (req, res) => {
  const db = readDb(); const project = projectOr404(db, req.params.id, res); if (!project) return
  try {
    const platform = platforms.find(p => p.id === project.platform)?.name || project.platform
    const queries = [`${project.name} ${project.category} 用户痛点 评测`, `${project.name} ${platform} 怎么选 使用`, `${project.category} 消费趋势 卖点`]
    const settled = await Promise.allSettled(queries.map(publicSearch))
    const sources = settled.flatMap(r => r.status === 'fulfilled' ? r.value : []).filter((s, i, arr) => arr.findIndex(x => x.url === s.url) === i).slice(0, 12)
    const insight = await callReasoning(db.settings, project, sources)
    project.insight = insight; project.progress = Math.max(project.progress, 38); project.updatedAt = new Date().toISOString(); writeDb(db); res.json(insight)
  } catch (error) { res.status(502).json({ error: error.message }) }
})
app.post('/api/compliance/scan', (req, res) => res.json(complianceScan(req.body.text || '')))

app.get('/api/models', async (req, res) => {
  try { res.json(await listModels(req.query.type === 'video' ? 'video' : 'image')) } catch (error) { res.status(502).json({ error: error.message }) }
})
app.get('/api/models/options', async (req, res) => {
  const type = req.query.type === 'video' ? 'video' : 'image'
  if (!req.query.model) return res.status(400).json({ error: '缺少模型' })
  try { res.json(await runBoli([type, 'options', '--model', req.query.model, '--json'])) } catch (error) { res.status(502).json({ error: error.message }) }
})

app.post('/api/generate/image/quote', async (req, res) => {
  const db = readDb(); const project = projectOr404(db, req.body.projectId, res); if (!project) return
  try {
    const models = await listModels('image'); if (!models.some(m => m.id === req.body.model)) throw new Error('模型别名已失效，请刷新后重选')
    const options = await runBoli(['image', 'options', '--model', req.body.model, '--json'])
    const modelParameters = options.parameters || options
    const key = id(`img_${project.id}`)
    const args = ['image', 'generate', '--model', req.body.model, '--prompt', req.body.prompt, '--idempotency-key', key,
      ...optionArgs(req.body, { ratio: '--ratio', resolution: '--resolution', quality: '--quality' })]
    const selectedAssets = (req.body.assetIds || []).map(assetId => project.assets.find(asset => asset.id === assetId)).filter(asset => asset?.mime?.startsWith('image'))
    if (!selectedAssets.length) throw new Error('必须选择至少一张商品参考图，系统已阻止无参考素材生成')
    if (modelParameters.supportReferenceImage === false) throw new Error('当前模型不支持参考图，请选择支持参考图的图片模型')
    const configuredBase = String(db.settings.assetPublicBaseUrl || '').replace(/\/$/, '')
    const maxReferences = Number(modelParameters.maxReferenceImages || 10)
    if (selectedAssets.length > maxReferences) throw new Error(`当前模型最多支持 ${maxReferences} 张参考图，请减少选择后重试`)
    const resolvedAssets = selectedAssets.map(asset => ({
      asset,
      url: asset.source === 'url' || /^https?:\/\//i.test(asset.url)
        ? asset.url
        : configuredBase ? `${configuredBase}${asset.url.startsWith('/') ? '' : '/'}${asset.url}` : null
    }))
    const unreachableAssets = resolvedAssets.filter(item => !isPublicHttpUrl(item.url))
    if (unreachableAssets.length) throw new Error(`有 ${unreachableAssets.length} 张已选素材仍是本地文件或非公网地址，图片模型无法访问。请在“模型与配置”填写可公网访问的 HTTPS 素材网关，或改用公网图片 URL；本次未报价、未扣费。`)
    const referenceUrls = [...new Set(resolvedAssets.map(item => item.url))]
    for (const url of referenceUrls) args.push('--reference-image', url)
    args.push('--json')
    const quoteResult = await runBoli(args)
    const quote = quoteResult.quote || quoteResult
    const record = { id: id('quote'), kind: 'image', projectId: project.id, idempotencyKey: key, request: { ...req.body }, quote, options, status: 'quoted', createdAt: new Date().toISOString() }
    db.quotes.push(record); writeDb(db); res.json(record)
  } catch (error) { res.status(502).json({ error: error.message }) }
})
app.post('/api/generate/image/confirm', async (req, res) => {
  const db = readDb(); const record = db.quotes.find(q => q.id === req.body.recordId && q.kind === 'image')
  if (!record || record.status !== 'quoted') return res.status(409).json({ error: '报价不存在、已使用或状态不可确认' })
  const project = projectOr404(db, record.projectId, res); if (!project) return
  try {
    const normalizedQuote = record.quote.quote || record.quote
    const quoteId = normalizedQuote.quoteId || normalizedQuote.id
    const filename = `${Date.now()}-${cleanName(req.body.outputName || 'ecommerce-image')}.png`
    const fullOutput = path.join(outputDir, filename)
    record.status = 'confirming'; writeDb(db)
    const result = await runBoli(['image', 'generate', '--quote', quoteId, '--confirm', '--wait', '--timeout', '600', '--output', fullOutput, '--json'], 660000)
    record.status = result.status === 'succeeded' || result.ok ? 'succeeded' : (result.status || 'unknown'); record.result = result
    if (record.status === 'succeeded' && fs.existsSync(fullOutput)) project.outputs.push({ id: id('out'), kind: 'image', name: req.body.outputName || '电商图片', url: `/generated/${filename}`, createdAt: new Date().toISOString(), meta: result })
    project.jobs.push({ id: record.id, kind: 'image', status: record.status, result }); project.progress = Math.max(project.progress, 62); project.updatedAt = new Date().toISOString(); writeDb(db); res.json({ record, project })
  } catch (error) { record.status = 'unknown'; record.error = error.message; writeDb(db); res.status(502).json({ error: `${error.message}。提交状态未知时请勿重复生成，请使用原记录查询。`, record }) }
})

app.post('/api/generate/video/quote', async (req, res) => {
  const db = readDb(); const project = projectOr404(db, req.body.projectId, res); if (!project) return
  try {
    const models = await listModels('video'); if (!models.some(m => m.id === req.body.model)) throw new Error('模型别名已失效，请刷新后重选')
    const options = await runBoli(['video', 'options', '--model', req.body.model, '--json'])
    const key = id(`vid_${project.id}`)
    const args = ['video', 'generate', '--model', req.body.model, '--prompt', req.body.prompt, '--idempotency-key', key,
      ...optionArgs(req.body, { duration: '--duration', ratio: '--ratio', resolution: '--resolution', generateAudio: '--generate-audio' }), '--json']
    const quoteResult = await runBoli(args)
    const quote = quoteResult.quote || quoteResult
    const record = { id: id('quote'), kind: 'video', projectId: project.id, idempotencyKey: key, request: { ...req.body }, quote, options, status: 'quoted', createdAt: new Date().toISOString() }
    db.quotes.push(record); writeDb(db); res.json(record)
  } catch (error) { res.status(502).json({ error: error.message }) }
})
app.post('/api/generate/video/confirm', async (req, res) => {
  const db = readDb(); const record = db.quotes.find(q => q.id === req.body.recordId && q.kind === 'video')
  if (!record || record.status !== 'quoted') return res.status(409).json({ error: '报价不存在、已使用或状态不可确认' })
  const project = projectOr404(db, record.projectId, res); if (!project) return
  const r = record.request
  try {
    record.status = 'confirming'; writeDb(db)
    const args = ['video', 'generate', '--model', r.model, '--prompt', r.prompt, '--idempotency-key', record.idempotencyKey,
      ...optionArgs(r, { duration: '--duration', ratio: '--ratio', resolution: '--resolution', generateAudio: '--generate-audio' }), '--yes', '--max-cost', String(req.body.maxCost), '--wait', '--timeout', '600', '--json']
    const result = await runBoli(args, 660000)
    record.status = result.status || (result.ok ? 'succeeded' : 'unknown'); record.result = result
    if (record.status === 'succeeded' && result.resultUrl) project.outputs.push({ id: id('out'), kind: 'video', name: req.body.outputName || '商品视频', url: result.resultUrl, createdAt: new Date().toISOString(), meta: result })
    project.jobs.push({ id: record.id, kind: 'video', status: record.status, result }); project.progress = Math.max(project.progress, 78); project.updatedAt = new Date().toISOString(); writeDb(db); res.json({ record, project })
  } catch (error) { record.status = 'unknown'; record.error = error.message; writeDb(db); res.status(502).json({ error: `${error.message}。提交状态未知时请勿重复生成，请使用原记录查询。`, record }) }
})
app.post('/api/generate/status', async (req, res) => {
  const db = readDb(); const record = db.quotes.find(q => q.id === req.body.recordId); if (!record) return res.status(404).json({ error: '记录不存在' })
  const jobId = record.result?.jobId || record.quote?.jobId || req.body.jobId; if (!jobId) return res.status(400).json({ error: '该记录暂时没有任务编号' })
  try { const result = await runBoli([record.kind, 'status', '--job', jobId, '--wait', '--timeout', '30', '--json'], 45000); record.result = result; record.status = result.status || record.status; writeDb(db); res.json(record) }
  catch (error) { res.status(502).json({ error: error.message, record }) }
})

app.get('/api/settings', (_req, res) => {
  const settings = readDb().settings
  res.json({ ...settings, reasoning: { ...settings.reasoning, apiKey: settings.reasoning.apiKey ? '••••••••' : '' } })
})
app.put('/api/settings', (req, res) => {
  const db = readDb(); const currentKey = db.settings.reasoning.apiKey
  db.settings = { ...db.settings, ...req.body, reasoning: { ...db.settings.reasoning, ...(req.body.reasoning || {}) } }
  if (req.body.reasoning?.apiKey === '••••••••') db.settings.reasoning.apiKey = currentKey
  writeDb(db); res.json({ ...db.settings, reasoning: { ...db.settings.reasoning, apiKey: db.settings.reasoning.apiKey ? '••••••••' : '' } })
})

if (fs.existsSync(path.join(root, 'dist'))) app.use(express.static(path.join(root, 'dist')))
app.use((req, res, next) => {
  if (req.path.startsWith('/api/')) return next()
  const index = path.join(root, 'dist', 'index.html'); if (fs.existsSync(index)) return res.sendFile(index); next()
})
app.use((error, _req, res, _next) => res.status(400).json({ error: error.message || '请求处理失败' }))

const port = Number(process.env.PORT || 8790)
app.listen(port, () => console.log(`Commerce Copilot API running at http://localhost:${port}`))
