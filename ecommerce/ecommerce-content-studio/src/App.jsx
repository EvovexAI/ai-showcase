import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Activity, AlertTriangle, Archive, ArrowLeft, ArrowRight, BadgeCheck, BarChart3, Box, BrainCircuit,
  Check, CheckCircle2, ChevronDown, ChevronRight, CircleDollarSign, Clapperboard, Cloud, Copy, Database,
  Download, Eye, FileImage, FileSearch, Film, FolderKanban, Gauge, Globe2, Grid2X2, Image, ImagePlus, Info,
  Languages, Layers3, LayoutDashboard, Link2, LoaderCircle, Menu, MessageSquareText, MonitorSmartphone, MoreHorizontal,
  PackageCheck, PanelTop, PencilLine, Play, Plus, RefreshCw, Rocket, Search, Settings2, ShieldCheck, Sparkles,
  Trash2, Upload, Video, WandSparkles, X, Zap
} from 'lucide-react'

const nav = [
  { id: 'dashboard', label: '项目总览', icon: LayoutDashboard },
  { id: 'research', label: '市场洞察', icon: BarChart3 },
  { id: 'assets', label: '素材中心', icon: Database },
  { id: 'creation', label: '智能创作', icon: WandSparkles },
  { id: 'compliance', label: '合规中心', icon: ShieldCheck },
  { id: 'settings', label: '模型与配置', icon: Settings2 }
]

const projectTabs = [
  { id: 'overview', label: '项目驾驶舱', icon: Gauge, group: '策划' },
  { id: 'insight', label: '全网洞察', icon: Globe2, group: '策划' },
  { id: 'assets', label: '多视角素材', icon: Layers3, group: '素材' },
  { id: 'main', label: '主图套装', icon: Image, group: '图片创作' },
  { id: 'sku', label: 'SKU 套图', icon: Grid2X2, group: '图片创作' },
  { id: 'detail', label: '详情页', icon: PanelTop, group: '图片创作' },
  { id: 'video', label: '视频工坊', icon: Clapperboard, group: '视频创作' },
  { id: 'review', label: '合规与交付', icon: PackageCheck, group: '交付' }
]

const assetKinds = [
  ['front', '商品正面', '正面结构与品牌信息'], ['top', '商品俯视', '顶部形态与尺寸关系'], ['side', '商品侧面', '厚度、接口与轮廓'],
  ['product', '其他商品图', '细节、包装和组合'], ['scene', '场景素材', '环境、背景与氛围'], ['prop', '道具素材', '搭配道具与陈列'],
  ['person', '人物素材', '模特、手持与动作'], ['footage', '实拍视频', '手拍演示与口播素材']
]

const api = async (url, options = {}) => {
  const response = await fetch(url, { ...options, headers: options.body instanceof FormData ? options.headers : { 'content-type': 'application/json', ...(options.headers || {}) } })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.error || `请求失败 (${response.status})`)
  }
  if (response.status === 204) return null
  return response.json()
}

function App() {
  const [page, setPage] = useState('dashboard')
  const [projects, setProjects] = useState([])
  const [platforms, setPlatforms] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [activeProject, setActiveProject] = useState(null)
  const [projectTab, setProjectTab] = useState('overview')
  const [createOpen, setCreateOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [toast, setToast] = useState(null)
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)

  const notify = (message, type = 'success') => { setToast({ message, type }); window.setTimeout(() => setToast(null), 3500) }
  const loadProjects = async () => {
    const data = await api('/api/projects'); setProjects(data)
    if (activeId) setActiveProject(data.find(p => p.id === activeId) || null)
  }
  const openProject = async (id, tab = 'overview') => {
    const project = await api(`/api/projects/${id}`); setActiveId(id); setActiveProject(project); setProjectTab(tab); setPage('project'); window.scrollTo(0, 0)
  }
  useEffect(() => {
    Promise.all([api('/api/projects'), api('/api/platforms'), api('/api/health').catch(() => null)]).then(([p, pl, h]) => { setProjects(p); setPlatforms(pl); setHealth(h) }).finally(() => setLoading(false))
  }, [])

  const selectNav = id => {
    setPage(id); setActiveId(null); setActiveProject(null); setSidebarOpen(false)
  }
  const createProject = async form => {
    const project = await api('/api/projects', { method: 'POST', body: JSON.stringify(form) })
    setProjects(v => [project, ...v]); setCreateOpen(false); notify('商品项目已创建'); openProject(project.id, 'assets')
  }
  const refreshProject = async () => {
    if (!activeId) return
    const project = await api(`/api/projects/${activeId}`); setActiveProject(project); setProjects(v => v.map(p => p.id === project.id ? project : p))
  }

  return <div className="app-shell">
    <Sidebar page={page} open={sidebarOpen} health={health} onNavigate={selectNav} onCreate={() => setCreateOpen(true)} onClose={() => setSidebarOpen(false)} />
    <main className="main-area">
      <Topbar page={page} project={activeProject} onMenu={() => setSidebarOpen(true)} onCreate={() => setCreateOpen(true)} onBack={() => selectNav('dashboard')} />
      {loading ? <FullLoader /> : page === 'project' && activeProject ?
        <ProjectWorkspace project={activeProject} tab={projectTab} setTab={setProjectTab} platforms={platforms} refresh={refreshProject} notify={notify} /> :
        <PageRouter page={page} projects={projects} platforms={platforms} health={health} openProject={openProject} onCreate={() => setCreateOpen(true)} loadProjects={loadProjects} notify={notify} />}
    </main>
    {createOpen && <CreateProjectModal platforms={platforms} onClose={() => setCreateOpen(false)} onCreate={createProject} />}
    {toast && <div className={`toast ${toast.type}`}><CheckCircle2 size={18} />{toast.message}</div>}
  </div>
}

function Sidebar({ page, open, health, onNavigate, onCreate, onClose }) {
  return <>
    <div className={`mobile-shade ${open ? 'show' : ''}`} onClick={onClose} />
    <aside className={`sidebar ${open ? 'open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Sparkles size={20} /></div><div><b>商策造物</b><span>Commerce Copilot</span></div><button className="icon-btn mobile-only" onClick={onClose}><X size={18} /></button></div>
      <button className="new-project" onClick={onCreate}><Plus size={18} /><span>新建商品项目</span><kbd>⌘ N</kbd></button>
      <nav className="primary-nav">{nav.map(item => <button key={item.id} className={page === item.id || (page === 'project' && item.id === 'dashboard') ? 'active' : ''} onClick={() => onNavigate(item.id)}><item.icon size={19} /><span>{item.label}</span>{item.id === 'creation' && <em>AI</em>}</button>)}</nav>
      <div className="sidebar-spacer" />
      <div className="system-mini">
        <div className="system-row"><span className={`status-dot ${health?.ok ? '' : 'off'}`} /><span>{health?.ok ? '生成引擎在线' : '生成引擎检查中'}</span><Activity size={15} /></div>
        <div className="system-meta"><span>BOLI 安全报价链路</span><b>{health?.boli?.balance?.toLocaleString?.() || '—'} 算力</b></div>
      </div>
      <div className="profile"><div className="avatar">创</div><div><b>创作工作台</b><span>专业版 · 本地部署</span></div><MoreHorizontal size={18} /></div>
    </aside>
  </>
}

function Topbar({ page, project, onMenu, onCreate, onBack }) {
  return <header className="topbar">
    <button className="icon-btn menu-btn" onClick={onMenu}><Menu size={20} /></button>
    <div className="breadcrumbs">{project ? <><button onClick={onBack}>商品项目</button><ChevronRight size={15}/><b>{project.name}</b></> : <><span>工作空间</span><ChevronRight size={15}/><b>{nav.find(n => n.id === page)?.label || '项目总览'}</b></>}</div>
    <div className="top-actions"><button className="search-pill"><Search size={16}/><span>搜索项目或素材</span><kbd>⌘ K</kbd></button><button className="icon-btn"><MessageSquareText size={18}/><i /></button><button className="button small" onClick={onCreate}><Plus size={16}/>新建项目</button></div>
  </header>
}

function PageRouter(props) {
  if (props.page === 'dashboard') return <Dashboard {...props} />
  if (props.page === 'settings') return <SettingsPage {...props} />
  if (props.page === 'compliance') return <ComplianceCenter {...props} />
  const mapping = {
    research: { icon: BarChart3, title: '市场洞察', desc: '把分散的公开网页信息整理成用户痛点、卖点证据与创作策略。', tab: 'insight', action: '开始全网分析' },
    assets: { icon: Database, title: '素材中心', desc: '统一管理商品多视角图、实拍视频、场景、道具与人物参考。', tab: 'assets', action: '上传新素材' },
    creation: { icon: WandSparkles, title: '智能创作', desc: '按平台、语言、尺寸和比例生成主图、SKU 套图、详情页与三类视频。', tab: 'main', action: '进入创作台' }
  }
  const info = mapping[props.page] || mapping.creation
  return <GenericHub {...props} {...info} />
}

function Dashboard({ projects, platforms, openProject, onCreate }) {
  const avg = projects.length ? Math.round(projects.reduce((s, p) => s + (p.progress || 0), 0) / projects.length) : 0
  const assets = projects.reduce((s, p) => s + (p.assets?.length || 0), 0)
  const outputs = projects.reduce((s, p) => s + (p.outputs?.length || 0), 0)
  return <div className="page dashboard-page">
    <section className="hero">
      <div className="eyebrow"><Sparkles size={15}/> AI 电商内容生产系统</div>
      <h1>让一个商品，长出一整套<br/><span>能卖货的内容。</span></h1>
      <p>从多视角商品素材到洞察、主图、详情页和视频，一套工作流适配多个电商平台。</p>
      <div className="hero-actions"><button className="button primary big" onClick={onCreate}><Plus size={19}/>创建首个商品项目</button><button className="button ghost big" onClick={() => document.querySelector('#projects')?.scrollIntoView({ behavior: 'smooth' })}><Play size={18}/>查看工作流</button></div>
      <div className="hero-orbit"><div className="orbit-ring one"/><div className="orbit-ring two"/><div className="cube c1"><Image size={22}/></div><div className="cube c2"><Video size={22}/></div><div className="cube c3"><BrainCircuit size={22}/></div><div className="core"><Box size={42}/><span>PRODUCT</span></div></div>
    </section>
    <section className="metrics-grid">
      <Metric icon={FolderKanban} label="商品项目" value={projects.length} suffix="个" tone="mint" trend="按商品独立管理" />
      <Metric icon={Database} label="素材总量" value={assets} suffix="份" tone="blue" trend="图片与实拍视频" />
      <Metric icon={WandSparkles} label="已生成内容" value={outputs} suffix="项" tone="purple" trend="图文与视频资产" />
      <Metric icon={Gauge} label="平均完成度" value={avg} suffix="%" tone="amber" trend="端到端生产进度" />
    </section>
    <section className="section-block" id="projects">
      <div className="section-title"><div><span>商品项目</span><h2>正在进行的创作</h2></div><div className="section-tools"><button className="chip active">全部 {projects.length}</button><button className="chip">创作中</button><button className="chip">已交付</button></div></div>
      {projects.length ? <div className="project-grid">{projects.map(p => <ProjectCard key={p.id} project={p} platform={platforms.find(x => x.id === p.platform)} onOpen={() => openProject(p.id)} />)}<button className="project-card add-card" onClick={onCreate}><div><Plus size={28}/></div><b>添加新商品</b><span>从图片与基础信息开始</span></button></div> : <EmptyProjects onCreate={onCreate} />}
    </section>
    <section className="workflow-section"><div className="section-title"><div><span>标准工作流</span><h2>从商品到全域内容，六步完成</h2></div></div><div className="workflow-line">
      {[['01','素材入库','正面 / 俯视 / 侧面'],['02','全网洞察','痛点 / 卖点 / 竞品'],['03','策略定稿','平台 / 语言 / 规格'],['04','图文生成','主图 / SKU / 详情'],['05','视频生成','主图 / 操作 / 营销'],['06','合规交付','违禁词 / 查重 / 导出']].map((x,i)=><div className="workflow-step" key={x[0]}><span>{x[0]}</span><b>{x[1]}</b><small>{x[2]}</small>{i<5&&<ArrowRight/>}</div>)}
    </div></section>
  </div>
}

function Metric({ icon: Icon, label, value, suffix, tone, trend }) { return <div className={`metric-card ${tone}`}><div className="metric-icon"><Icon size={21}/></div><div><span>{label}</span><strong>{value}<small>{suffix}</small></strong><em>{trend}</em></div></div> }
function ProjectCard({ project, platform, onOpen }) {
  const cover = project.outputs?.find(o => o.kind === 'image')?.url || project.assets?.find(a => a.mime?.startsWith('image'))?.url
  return <button className="project-card" onClick={onOpen}>
    <div className={`project-cover ${cover ? 'has-cover' : ''}`} style={cover ? { backgroundImage: `url(${cover})` } : {}}>{!cover&&<><Box size={42}/><span>等待商品素材</span></>}<div className="cover-top"><span style={{'--accent':platform?.accent}}>{platform?.name||'未选平台'}</span><MoreHorizontal size={18}/></div><div className="progress-badge">{project.progress||0}%</div></div>
    <div className="project-info"><div><b>{project.name}</b><span>{project.category} · {project.language === 'en-US' ? 'English' : '简体中文'}</span></div><ChevronRight size={19}/></div>
    <div className="project-footer"><span><Layers3 size={14}/>{project.assets?.length||0} 素材</span><span><Sparkles size={14}/>{project.outputs?.length||0} 成果</span><time>{new Date(project.updatedAt).toLocaleDateString('zh-CN')}</time></div>
  </button>
}
function EmptyProjects({ onCreate }) { return <div className="empty-projects"><div className="empty-visual"><div/><div/><Box size={44}/></div><h3>从一款商品开始</h3><p>上传正面、俯视和侧面图，系统会引导你完成整套电商内容。</p><button className="button primary" onClick={onCreate}><Plus size={18}/>新建商品项目</button></div> }

function GenericHub({ icon: Icon, title, desc, action, tab, projects, platforms, openProject, onCreate }) {
  return <div className="page"><section className="hub-hero"><div className="hub-icon"><Icon size={28}/></div><div><span>跨项目工作台</span><h1>{title}</h1><p>{desc}</p></div><button className="button primary" onClick={projects.length ? () => openProject(projects[0].id, tab) : onCreate}>{action}<ArrowRight size={17}/></button></section>
    <div className="section-title compact"><div><span>商品项目</span><h2>选择要处理的项目</h2></div></div>
    {projects.length ? <div className="list-stack">{projects.map(project => <button className="hub-project" key={project.id} onClick={() => openProject(project.id, tab)}><div className="mini-cover">{project.assets?.find(a=>a.mime?.startsWith('image')) ? <img src={project.assets.find(a=>a.mime?.startsWith('image')).url}/> : <Box/>}</div><div><b>{project.name}</b><span>{project.category} · {platforms.find(p=>p.id===project.platform)?.name}</span></div><div className="hub-stats"><span>{project.assets?.length||0} 素材</span><span>{project.outputs?.length||0} 成果</span></div><div className="ring-progress" style={{'--p':`${project.progress||0}%`}}><span>{project.progress||0}</span></div><ChevronRight/></button>)}</div> : <EmptyProjects onCreate={onCreate}/>}</div>
}

function ProjectWorkspace({ project, tab, setTab, platforms, refresh, notify }) {
  const currentPlatform = platforms.find(p => p.id === project.platform)
  const groups = [...new Set(projectTabs.map(t => t.group))]
  return <div className="workspace-layout">
    <aside className="project-rail">
      <div className="project-identity"><div className="project-thumb">{project.assets?.find(a=>a.mime?.startsWith('image')) ? <img src={project.assets.find(a=>a.mime?.startsWith('image')).url}/> : <Box/>}</div><div><b>{project.name}</b><span>{currentPlatform?.name}</span></div></div>
      <div className="progress-panel"><div><span>项目完成度</span><b>{project.progress||0}%</b></div><div className="progress-track"><i style={{width:`${project.progress||0}%`}}/></div></div>
      {groups.map(group => <div className="rail-group" key={group}><label>{group}</label>{projectTabs.filter(t=>t.group===group).map(item=><button key={item.id} className={tab===item.id?'active':''} onClick={()=>setTab(item.id)}><item.icon size={17}/><span>{item.label}</span>{tab===item.id&&<i/>}</button>)}</div>)}
    </aside>
    <div className="workspace-content">
      {tab === 'overview' && <ProjectOverview project={project} platform={currentPlatform} setTab={setTab} />}
      {tab === 'insight' && <InsightStudio project={project} refresh={refresh} notify={notify} />}
      {tab === 'assets' && <AssetStudio project={project} refresh={refresh} notify={notify} />}
      {['main','sku','detail'].includes(tab) && <ImageStudio project={project} tab={tab} platform={currentPlatform} refresh={refresh} notify={notify} />}
      {tab === 'video' && <VideoStudio project={project} platform={currentPlatform} refresh={refresh} notify={notify} />}
      {tab === 'review' && <DeliveryStudio project={project} platform={currentPlatform} notify={notify} />}
    </div>
  </div>
}

function ProjectOverview({ project, platform, setTab }) {
  const stages = [
    { id:'assets', title:'01 素材准备', desc:'上传商品与创意参考', done:project.assets?.length>=3, value:`${project.assets?.length||0} 份` },
    { id:'insight', title:'02 全网洞察', desc:'洞察痛点与卖点', done:!!project.insight, value:project.insight?'已完成':'待分析' },
    { id:'main', title:'03 图文套装', desc:'主图、SKU 与详情页', done:project.outputs?.some(o=>o.kind==='image'), value:`${project.outputs?.filter(o=>o.kind==='image').length||0} 张` },
    { id:'video', title:'04 视频矩阵', desc:'主图、操作与营销视频', done:project.outputs?.some(o=>o.kind==='video'), value:`${project.outputs?.filter(o=>o.kind==='video').length||0} 条` },
    { id:'review', title:'05 合规交付', desc:'违禁词、查重与导出', done:false, value:'待检查' }
  ]
  return <div className="workspace-page"><PageHeading eyebrow="PROJECT COCKPIT" title={project.name} desc={`${project.category} · ${platform?.name} · ${project.language==='en-US'?'English':'简体中文'}`} action={<button className="button primary" onClick={()=>setTab('assets')}><Upload size={17}/>继续制作</button>} />
    <div className="overview-banner"><div><span className="live-badge"><i/>创作流程已就绪</span><h3>下一步：{project.assets?.length < 3 ? '补齐商品多视角素材' : !project.insight ? '运行全网市场分析' : '开始生成商品主图'}</h3><p>系统将使用项目中的平台、语言和素材配置，保持整套内容一致。</p></div><div className="score-orb"><strong>{project.progress||0}</strong><span>完成度</span></div></div>
    <div className="stage-grid">{stages.map(s=><button key={s.id} className={`stage-card ${s.done?'done':''}`} onClick={()=>setTab(s.id)}><div className="stage-status">{s.done?<Check size={15}/>:<span/>}</div><small>{s.title}</small><b>{s.desc}</b><footer><span>{s.value}</span><ArrowRight size={16}/></footer></button>)}</div>
    <div className="two-col"><div className="panel"><PanelTitle icon={Sparkles} title="内容规划" subtitle="项目预计交付清单"/><div className="deliverable-list">{[['主图',`${project.brief?.mainCount||5} 张`],['SKU 套图',`${project.brief?.skuCount||6} 张`],['详情页',`${project.brief?.detailCount||8} 屏`],['视频','3 种类型'],['多端适配',(project.brief?.ratios||[]).join(' / ')]].map(x=><div key={x[0]}><span>{x[0]}</span><b>{x[1]}</b></div>)}</div></div><div className="panel"><PanelTitle icon={MonitorSmartphone} title="平台规范" subtitle={platform?.name}/><div className="platform-spec"><strong style={{color:platform?.accent}}>{platform?.main}</strong><span>建议主图规格</span>{platform?.rules?.map(r=><p key={r}><CheckCircle2 size={15}/>{r}</p>)}</div></div></div>
  </div>
}

function InsightStudio({ project, refresh, notify }) {
  const [running, setRunning] = useState(false)
  const run = async () => { setRunning(true); try { await api(`/api/projects/${project.id}/analyze`, {method:'POST',body:'{}'}); await refresh(); notify('全网分析完成，洞察已写入项目') } catch(e){ notify(e.message,'error') } finally { setRunning(false) } }
  const insight = project.insight
  return <div className="workspace-page"><PageHeading eyebrow="MARKET INTELLIGENCE" title="全网洞察与策略" desc="从公开网页检索竞品表达、用户关注点和使用场景，再由推理模型形成可执行策略。" action={<button className="button primary" onClick={run} disabled={running}>{running?<LoaderCircle className="spin" size={17}/>:<RefreshCw size={17}/>} {insight?'重新分析':'开始全网分析'}</button>} />
    {!insight ? <div className="analysis-empty"><div className="radar"><span/><span/><span/><Globe2 size={42}/></div><h3>让创作先建立在洞察上</h3><p>系统会以商品名、品类和目标平台组合检索词，抓取公开结果并提炼痛点、卖点与内容方向。</p><div className="analysis-features"><span><Search/>多关键词公开检索</span><span><BrainCircuit/>结构化推理</span><span><FileSearch/>来源可追溯</span></div></div> : <>
      <div className="insight-summary"><div className="eyebrow"><Sparkles size={14}/>策略摘要</div><h3>{insight.summary}</h3><div className="keyword-row">{insight.keywords?.map(k=><span key={k}>{k}</span>)}</div></div>
      <div className="insight-grid"><InsightList tone="danger" icon={AlertTriangle} title="核心痛点" items={insight.painPoints}/><InsightList tone="mint" icon={Zap} title="核心卖点" items={insight.sellingPoints}/></div>
      <div className="panel"><PanelTitle icon={BrainCircuit} title="创意方向" subtitle="把洞察转译为画面"/><div className="direction-grid">{insight.creativeDirections?.map((d,i)=><div key={i}><span>0{i+1}</span><b>{d.title}</b><p>{d.detail}</p></div>)}</div></div>
      <div className="two-col"><div className="panel"><PanelTitle icon={Languages} title="人群画像" subtitle={`${insight.personas?.length||0} 类重点人群`}/><div className="persona-list">{insight.personas?.map((p,i)=><div key={i}><div>{p.name?.slice(0,1)}</div><section><b>{p.name}</b><p>需求：{p.need}</p><span>顾虑：{p.concern}</span></section></div>)}</div></div><div className="panel"><PanelTitle icon={Link2} title="检索来源" subtitle={`${insight.sourceCount||0} 条公开结果`}/><div className="source-list">{insight.sources?.slice(0,6).map((s,i)=><a href={s.url} target="_blank" rel="noreferrer" key={i}><span>{i+1}</span><div><b>{s.title}</b><p>{s.snippet}</p></div><ArrowRight size={15}/></a>)}</div></div></div>
    </>}
  </div>
}
function InsightList({tone,icon:Icon,title,items=[]}) { return <div className={`panel insight-list ${tone}`}><PanelTitle icon={Icon} title={title} subtitle={`${items.length} 个重点`}/>{items.map((x,i)=><div className="insight-item" key={i}><span>{String(i+1).padStart(2,'0')}</span><p>{x}</p></div>)}</div> }

function AssetStudio({ project, refresh, notify }) {
  const input = useRef()
  const [kind,setKind] = useState('front'); const [busy,setBusy]=useState(false); const [url,setUrl]=useState('')
  const uploadFiles = async files => { if(!files.length)return; setBusy(true); const fd=new FormData(); [...files].forEach(f=>fd.append('files',f)); fd.append('kind',kind); try{await api(`/api/projects/${project.id}/assets`,{method:'POST',body:fd});await refresh();notify(`已上传 ${files.length} 份素材`)}catch(e){notify(e.message,'error')}finally{setBusy(false)} }
  const addUrl = async () => { if(!url)return; setBusy(true); try{await api(`/api/projects/${project.id}/assets/url`,{method:'POST',body:JSON.stringify({url,kind})});setUrl('');await refresh();notify('外部素材已加入项目')}catch(e){notify(e.message,'error')}finally{setBusy(false)} }
  const remove = async id => { try{await api(`/api/projects/${project.id}/assets/${id}`,{method:'DELETE'});await refresh();notify('素材已移除')}catch(e){notify(e.message,'error')} }
  const changeKind = async (id,nextKind) => { try{await api(`/api/projects/${project.id}/assets/${id}`,{method:'PATCH',body:JSON.stringify({kind:nextKind})});await refresh();notify('素材视角已更新')}catch(e){notify(e.message,'error')} }
  return <div className="workspace-page"><PageHeading eyebrow="ASSET LIBRARY" title="多视角素材中心" desc="上传真实商品、场景、道具、人物和实拍视频；生成时可按需勾选。" action={<button className="button primary" onClick={()=>input.current?.click()}><Upload size={17}/>上传素材</button>}/>
    <input hidden multiple type="file" accept="image/*,video/*" ref={input} onChange={e=>uploadFiles(e.target.files)}/>
    <div className="asset-type-strip">{assetKinds.map(x=><button key={x[0]} className={kind===x[0]?'active':''} onClick={()=>setKind(x[0])}><span>{project.assets?.filter(a=>a.kind===x[0]).length||0}</span><b>{x[1]}</b><small>{x[2]}</small></button>)}</div>
    <div className="upload-zone" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();uploadFiles(e.dataTransfer.files)}} onClick={()=>input.current?.click()}><div className="upload-icon">{busy?<LoaderCircle className="spin"/>:<ImagePlus/>}</div><div><b>{busy?'正在导入素材…':'拖拽素材到这里，或点击选择文件'}</b><span>支持 JPG、PNG、WEBP、MP4；单文件最大 200MB</span></div><button className="button ghost" type="button">选择文件</button></div>
    <div className="url-import"><Link2 size={18}/><input value={url} onChange={e=>setUrl(e.target.value)} placeholder="也可粘贴公网图片 URL（可直接用于参考图生成）"/><button className="button small" onClick={addUrl} disabled={!url||busy}>加入项目</button></div>
    <div className="section-title compact"><div><span>CURRENT ASSETS</span><h2>项目素材 · {project.assets?.length||0}</h2></div><div className="notice-pill"><Info size={14}/>本地上传需部署公网素材域名后才能作为 BOLI 参考图</div></div>
    {project.assets?.length ? <div className="asset-grid">{project.assets.map(a=><div className="asset-card" key={a.id}><div className="asset-preview">{a.mime?.startsWith('video')?<video src={a.url}/>:<img src={a.url}/>}<span>{assetKinds.find(x=>x[0]===a.kind)?.[1]||a.kind}</span><div className="asset-actions"><button onClick={()=>window.open(a.url)}><Eye/></button><button onClick={()=>remove(a.id)}><Trash2/></button></div></div><b title={a.name}>{a.name}</b><small>{a.source==='url'?'公网参考':'本地素材'} · {a.size?formatBytes(a.size):'URL'}</small><select className="asset-kind-select" value={a.kind} onChange={e=>changeKind(a.id,e.target.value)}>{assetKinds.map(x=><option key={x[0]} value={x[0]}>{x[1]}</option>)}</select></div>)}</div> : <div className="mini-empty"><ImagePlus/><b>还没有素材</b><span>建议至少上传正面、俯视和侧面图。</span></div>}
  </div>
}

function ImageStudio({ project, tab, platform, refresh, notify }) {
  const labels={main:['主图套装','用 5 张图完成从第一眼吸引到细节消疑。'],sku:['SKU 套图','统一不同颜色、规格和组合的视觉表达。'],detail:['详情页编排','按说服逻辑生成可拆分的长页内容模块。']}
  const productImages = useMemo(()=>project.assets.filter(a=>a.mime?.startsWith('image')&&['front','top','side','product'].includes(a.kind)),[project.assets])
  const [models,setModels]=useState([]); const [modelOptions,setModelOptions]=useState(null); const [loading,setLoading]=useState(false); const [quote,setQuote]=useState(null); const [selectedAssets,setSelectedAssets]=useState(()=>productImages.slice(0,10).map(a=>a.id)); const [assetGateway,setAssetGateway]=useState('')
  const [form,setForm]=useState({model:'',ratio:tab==='detail'?'3:4':'1:1',resolution:'1K',quality:'',prompt:''})
  const chooseModel=async model=>{setForm(f=>({...f,model}));try{const result=await api(`/api/models/options?type=image&model=${encodeURIComponent(model)}`);const p=result.parameters||result;setModelOptions(p);setForm(f=>({...f,model,ratio:p.supportedRatios?.includes(f.ratio)?f.ratio:(p.defaults?.ratio||p.supportedRatios?.[0]||f.ratio),resolution:p.supportedResolutions?.includes(f.resolution)?f.resolution:(p.defaults?.resolution||p.supportedResolutions?.[0]||f.resolution),quality:p.supportedQualities?.includes(f.quality)?f.quality:(p.defaults?.quality||'')}))}catch(e){notify(e.message,'error')}}
  useEffect(()=>{api('/api/models?type=image').then(m=>{setModels(m);if(m[0])chooseModel(m[0].id)}).catch(e=>notify(e.message,'error'))},[])
  useEffect(()=>{setForm(f=>({...f,ratio:tab==='detail'?'3:4':'1:1',prompt:defaultImagePrompt(project,tab,platform)}))},[tab,project.id])
  useEffect(()=>{setSelectedAssets(productImages.slice(0,10).map(a=>a.id))},[project.id])
  useEffect(()=>{api('/api/settings').then(s=>setAssetGateway(s.assetPublicBaseUrl||'')).catch(()=>setAssetGateway(''))},[])
  const isPublicReference = value => { try { const u=new URL(value); const h=u.hostname.toLowerCase(); if(!['http:','https:'].includes(u.protocol)||h==='localhost'||h.endsWith('.local')||h==='::1'||/^127\./.test(h)||/^10\./.test(h)||/^192\.168\./.test(h))return false; const m=h.match(/^172\.(\d+)\./); return !(m&&Number(m[1])>=16&&Number(m[1])<=31) } catch { return false } }
  const selectedRecords = project.assets.filter(a=>selectedAssets.includes(a.id))
  const referenceUrls = selectedRecords.filter(a=>a.source==='url'&&isPublicReference(a.url)).map(a=>a.url)
  const localSelected = selectedRecords.filter(a=>a.source!=='url').length
  const invalidRemoteSelected = selectedRecords.filter(a=>a.source==='url'&&!isPublicReference(a.url)).length
  const gatewayReady = isPublicReference(assetGateway)
  const referencesReady = selectedAssets.length>0&&modelOptions?.supportReferenceImage!==false&&!invalidRemoteSelected&&(!localSelected||gatewayReady)
  const getQuote = async()=>{if(!referencesReady){notify('参考素材尚未就绪，系统已阻止无参考素材报价','error');return}setLoading(true);try{const q=await api('/api/generate/image/quote',{method:'POST',body:JSON.stringify({...form,projectId:project.id,referenceUrls,assetIds:selectedAssets})});setQuote(q)}catch(e){notify(e.message,'error')}finally{setLoading(false)}}
  const confirm=async()=>{setLoading(true);try{await api('/api/generate/image/confirm',{method:'POST',body:JSON.stringify({recordId:quote.id,outputName:`${project.name}-${labels[tab][0]}`})});setQuote(null);await refresh();notify('图片生成完成并已加入项目成果')}catch(e){notify(e.message,'error')}finally{setLoading(false)}}
  return <div className="workspace-page studio-page"><PageHeading eyebrow="IMAGE STUDIO" title={labels[tab][0]} desc={labels[tab][1]} action={<span className="secure-tag"><ShieldCheck size={16}/>逐次报价 · 确认后扣费</span>}/>
    <div className="studio-layout"><div className="studio-controls">
      <div className="control-section"><label>01 · 平台与语言</label><div className="platform-lock"><span style={{background:platform?.accent}}>{platform?.name?.slice(0,1)}</span><div><b>{platform?.name}</b><small>{project.language==='en-US'?'English':'简体中文'} · {platform?.main}</small></div><BadgeCheck/></div></div>
      <div className="control-section"><label>02 · 选择生成模型</label><select value={form.model} onChange={e=>chooseModel(e.target.value)}>{models.map(m=><option key={m.id}>{m.id}</option>)}</select><small className="field-help">模型列表与规格每次从 BOLI 实时读取，不使用过期别名。</small></div>
      <div className="control-section"><label>03 · 画面规格</label><div className="segmented">{(modelOptions?.supportedRatios||['1:1','3:4','4:3','9:16','16:9']).map(x=><button className={form.ratio===x?'active':''} onClick={()=>setForm({...form,ratio:x})} key={x}>{x}</button>)}</div><div className="inline-fields"><select value={form.resolution} onChange={e=>setForm({...form,resolution:e.target.value})}>{(modelOptions?.supportedResolutions||['1K','2K','4K']).map(x=><option key={x}>{x}</option>)}</select><select value={form.quality} onChange={e=>setForm({...form,quality:e.target.value})}><option value="">默认画质</option>{(modelOptions?.supportedQualities||[]).map(x=><option key={x} value={x}>{x}</option>)}</select></div></div>
      <div className="control-section"><label>04 · 使用项目素材 <em>{selectedAssets.length} 已选</em></label><div className="asset-picker">{productImages.map(a=><button key={a.id} className={selectedAssets.includes(a.id)?'selected':''} onClick={()=>setSelectedAssets(v=>v.includes(a.id)?v.filter(x=>x!==a.id):[...v,a.id].slice(0,modelOptions?.maxReferenceImages||10))}><img src={a.url}/>{selectedAssets.includes(a.id)&&<Check/>}{a.source!=='url'&&!gatewayReady&&<i title="本地素材尚无公网地址，暂时不能传给模型">!</i>}</button>)}{!productImages.length&&<span className="field-help">请先到素材中心上传并标记商品正面、俯视或侧面图</span>}</div>{referencesReady?<div className="reference-ready"><CheckCircle2/>报价时将真实提交 {selectedAssets.length} 张商品参考图，模型必须保持杯型、花纹、配色与把手结构一致。</div>:<div className="reference-blocked"><AlertTriangle/><span>{modelOptions?.supportReferenceImage===false?'当前模型不支持参考图，请更换模型。':!selectedAssets.length?'请至少选择一张商品参考图。':invalidRemoteSelected?'所选外部素材不是模型可访问的公网地址。':'所选素材仍是本地文件，请到“模型与配置”填写公网 HTTPS 素材网关；在此之前系统不会报价或扣费。'}</span></div>}</div>
      <div className="control-section"><label>05 · 创作指令</label><textarea rows="9" value={form.prompt} onChange={e=>setForm({...form,prompt:e.target.value})}/></div>
      <button className="button primary full big" disabled={loading||!form.model||!form.prompt||!referencesReady} onClick={getQuote}>{loading?<LoaderCircle className="spin"/>:<CircleDollarSign/>}{referencesReady?'获取本次精确报价':'参考素材尚未就绪'}</button>
    </div><div className="studio-canvas">
      <div className="canvas-top"><div><span className="status-dot"/>创作预览</div><div><button><RefreshCw/></button><button><MonitorSmartphone/></button><button><MoreHorizontal/></button></div></div>
      {project.outputs?.filter(o=>o.kind==='image').length ? <div className={`output-masonry ${tab}`} >{project.outputs.filter(o=>o.kind==='image').map(o=><div key={o.id}><img src={o.url}/><div><span>{o.name}</span><button onClick={()=>window.open(o.url)}><Download/></button></div></div>)}</div> : <div className="canvas-empty"><div className="canvas-placeholder"><Image size={42}/><span/><span/></div><h3>你的创作会出现在这里</h3><p>配置左侧参数并获取报价，确认后开始生成。</p><div className="canvas-specs"><span><b>{form.ratio}</b>比例</span><span><b>{form.resolution}</b>清晰度</span><span><b>{project.language==='en-US'?'EN':'中'}</b>语言</span></div></div>}
    </div></div>
    {quote&&<QuoteModal record={quote} kind="image" loading={loading} onClose={()=>setQuote(null)} onConfirm={confirm}/>} 
  </div>
}

function VideoStudio({ project, platform, refresh, notify }) {
  const [type,setType]=useState('主图视频'); const [models,setModels]=useState([]); const [modelOptions,setModelOptions]=useState(null); const [loading,setLoading]=useState(false); const [quote,setQuote]=useState(null)
  const [form,setForm]=useState({model:'',duration:10,ratio:'9:16',resolution:'1080p',generateAudio:true,prompt:''})
  const chooseModel=async model=>{setForm(f=>({...f,model}));try{const result=await api(`/api/models/options?type=video&model=${encodeURIComponent(model)}`);const p=result.parameters||result;setModelOptions(p);setForm(f=>({...f,model,duration:p.supportedDurations?.includes(f.duration)?f.duration:(p.defaults?.duration||p.supportedDurations?.[0]||f.duration),ratio:p.supportedRatios?.includes(f.ratio)?f.ratio:(p.defaults?.ratio||p.supportedRatios?.[0]||f.ratio),resolution:p.defaults?.resolution||p.supportedResolutions?.[0]||f.resolution,generateAudio:p.supportGenerateAudio===false?false:f.generateAudio}))}catch(e){notify(e.message,'error')}}
  useEffect(()=>{api('/api/models?type=video').then(m=>{setModels(m);const preferred=m.find(x=>x.id==='seedance-mini-hd')||m[0];setForm(f=>({...f,prompt:defaultVideoPrompt(project,'主图视频',platform)}));if(preferred)chooseModel(preferred.id)}).catch(e=>notify(e.message,'error'))},[])
  const changeType=t=>{setType(t);setForm(f=>({...f,prompt:defaultVideoPrompt(project,t,platform)}))}
  const getQuote=async()=>{setLoading(true);try{setQuote(await api('/api/generate/video/quote',{method:'POST',body:JSON.stringify({...form,projectId:project.id})}))}catch(e){notify(e.message,'error')}finally{setLoading(false)}}
  const confirm=async()=>{setLoading(true);try{const cost=quote.quote.cost??quote.quote.finalCost??quote.quote.originalCost;await api('/api/generate/video/confirm',{method:'POST',body:JSON.stringify({recordId:quote.id,maxCost:cost,outputName:`${project.name}-${type}`})});setQuote(null);await refresh();notify('视频生成完成并已加入项目成果')}catch(e){notify(e.message,'error')}finally{setLoading(false)}}
  return <div className="workspace-page studio-page"><PageHeading eyebrow="VIDEO STUDIO" title="视频创作工坊" desc="分别创作主图视频、操作使用视频与营销视频；每条视频独立报价与确认。" action={<span className="secure-tag"><ShieldCheck size={16}/>每条视频单独授权</span>}/>
    <div className="video-type-tabs">{[['主图视频',Play,'快速展示卖点'],['操作视频',MonitorSmartphone,'步骤清晰易懂'],['营销视频',Rocket,'情绪与转化兼顾']].map(([t,I,d])=><button className={type===t?'active':''} onClick={()=>changeType(t)} key={t}><I/><div><b>{t}</b><span>{d}</span></div>{type===t&&<CheckCircle2/>}</button>)}</div>
    <div className="studio-layout"><div className="studio-controls">
      <div className="control-section"><label>01 · 视频模型</label><select value={form.model} onChange={e=>chooseModel(e.target.value)}>{models.map(m=><option key={m.id}>{m.id}</option>)}</select><small className="field-help">当前 BOLI CLI 为文生视频；项目素材会用于策划，但不会绕过 CLI 强行做图生视频。</small></div>
      <div className="control-section"><label>02 · 视频规格</label><div className="segmented">{(modelOptions?.supportedDurations||[5,10,15]).filter((x,i,a)=>a.length<=5||i===0||i===a.length-1||x%5===0).map(x=><button className={form.duration===x?'active':''} onClick={()=>setForm({...form,duration:x})} key={x}>{x}s</button>)}</div><div className="inline-fields"><select value={form.ratio} onChange={e=>setForm({...form,ratio:e.target.value})}>{(modelOptions?.supportedRatios||['9:16','16:9','1:1']).map(x=><option key={x}>{x}</option>)}</select><select value={form.resolution} onChange={e=>setForm({...form,resolution:e.target.value})}>{(modelOptions?.supportedResolutions||['720p','1080p']).map(x=><option key={x}>{x}</option>)}</select></div><label className="switch-row"><span><b>生成音频</b><small>环境声、动作音效或旁白</small></span><input type="checkbox" disabled={modelOptions?.supportGenerateAudio===false} checked={form.generateAudio} onChange={e=>setForm({...form,generateAudio:e.target.checked})}/><i/></label></div>
      <div className="control-section"><label>03 · 分秒视频脚本</label><textarea rows="14" value={form.prompt} onChange={e=>setForm({...form,prompt:e.target.value})}/></div>
      <button className="button primary full big" disabled={loading||!form.model} onClick={getQuote}>{loading?<LoaderCircle className="spin"/>:<CircleDollarSign/>}获取视频精确报价</button>
    </div><div className="studio-canvas dark-canvas"><div className="video-stage">{project.outputs?.filter(o=>o.kind==='video').length?<video controls src={project.outputs.filter(o=>o.kind==='video').at(-1).url}/>:<><div className="phone-frame"><div className="phone-screen"><Play size={34}/><div className="frame-grid"/></div></div><h3>{type}预览</h3><p>{form.duration} 秒 · {form.ratio} · {form.resolution}</p></>}</div><div className="timeline"><div className="timeline-ruler">{Array.from({length:6}).map((_,i)=><span key={i}>{Math.round(form.duration*i/5)}s</span>)}</div><div className="timeline-track"><i style={{width:'22%'}}/><b/><b/><b/></div><div className="timeline-notes"><span>主体亮相</span><span>利益点演示</span><span>行动引导</span></div></div></div></div>
    {quote&&<QuoteModal record={quote} kind="video" loading={loading} onClose={()=>setQuote(null)} onConfirm={confirm}/>} 
  </div>
}

function QuoteModal({ record, kind, loading, onClose, onConfirm }) {
  const q=record.quote?.quote||record.quote||{}; const cost=q.finalCost??q.cost??q.originalCost??'—'; const original=q.originalCost??cost; const balance=q.balance??q.currentBalance??'—'; const expires=q.expiresAt?new Date(q.expiresAt).toLocaleString('zh-CN'):'以服务端报价为准'
  return <Modal onClose={loading?()=>{}:onClose} className="quote-modal"><div className="quote-head"><div><CircleDollarSign/><span>精确报价</span></div><h2>确认本次{kind==='video'?'视频':'图片'}生成</h2><p>报价本身不扣费。只有点击下方确认后，才会提交这一笔生成。</p></div><div className="quote-cost"><span>本次费用</span><strong>{cost}<small> 算力</small></strong>{original!==cost&&<del>原价 {original}</del>}</div><div className="quote-details"><div><span>报价编号</span><b>{q.quoteId||q.id||'—'}</b></div><div><span>模型</span><b>{record.request.model}</b></div><div><span>规格</span><b>{record.request.ratio} · {record.request.resolution} {record.request.duration?`· ${record.request.duration}s`:''}</b></div><div><span>当前余额</span><b>{balance} 算力</b></div><div><span>有效期至</span><b>{expires}</b></div></div><div className="quote-warning"><ShieldCheck/><p>本次确认只对这份报价有效，不会授权未来生成。若报价过期，系统会要求重新报价。</p></div><div className="modal-actions"><button className="button ghost" onClick={onClose} disabled={loading}>暂不生成</button><button className="button primary" onClick={onConfirm} disabled={loading}>{loading?<LoaderCircle className="spin"/>:<Zap/>}确认并开始生成</button></div></Modal>
}

function DeliveryStudio({ project, platform, notify }) {
  const [text,setText]=useState([project.name,project.description,project.insight?.summary,...(project.insight?.sellingPoints||[])].filter(Boolean).join('\n')); const [result,setResult]=useState(null); const [busy,setBusy]=useState(false)
  const scan=async()=>{setBusy(true);try{setResult(await api('/api/compliance/scan',{method:'POST',body:JSON.stringify({text,platform:project.platform})}));notify('违禁词初筛完成')}catch(e){notify(e.message,'error')}finally{setBusy(false)}}
  return <div className="workspace-page"><PageHeading eyebrow="COMPLIANCE & DELIVERY" title="合规检查与交付" desc={`针对 ${platform?.name} 的发布前检查工作台。`} action={<button className="button primary" onClick={scan}>{busy?<LoaderCircle className="spin"/>:<ShieldCheck/>}立即检查</button>}/>
    <div className="compliance-score-row"><div className="score-card"><div className="score-ring"><strong>{result?.score??'—'}</strong><span>合规分</span></div><div><b>{result?result.hits.length?'发现需处理表达':'未发现内置风险词':'等待检查'}</b><p>覆盖极限词、医疗功效、绝对承诺和价格误导等基础规则。</p></div></div><div className="check-stats"><div><FileSearch/><span>查重状态</span><b>待接入版权库</b></div><div><Languages/><span>当前语言</span><b>{project.language==='en-US'?'English':'简体中文'}</b></div><div><PanelTop/><span>目标平台</span><b>{platform?.name}</b></div></div></div>
    <div className="two-col compliance-edit"><div className="panel"><PanelTitle icon={PencilLine} title="待检查文案" subtitle="可粘贴标题、卖点和详情文案"/><textarea rows="18" value={text} onChange={e=>setText(e.target.value)} placeholder="输入需要检查的电商文案…"/></div><div className="panel"><PanelTitle icon={ShieldCheck} title="风险结果" subtitle={result?`${result.hits.length} 处命中`:'尚未运行'}/>{result?<div className="risk-list">{result.hits.length?result.hits.map((h,i)=><div key={i}><span className={h.severity}>{h.word}</span><div><b>{h.reason}</b><p>建议改为可验证、有限定条件的客观表达。</p></div></div>):<div className="clean-result"><CheckCircle2/><b>未命中内置风险词</b><p>仍建议在正式发布前按平台最新规则人工复核。</p></div>}<small>{result.scope}</small></div>:<div className="mini-empty"><ShieldCheck/><b>等待扫描</b><span>检查后会逐条标出风险表达和原因。</span></div>}</div></div>
    <div className="panel"><PanelTitle icon={Archive} title="项目成果包" subtitle={`${project.outputs?.length||0} 项内容`}/><div className="delivery-grid">{project.outputs?.map(o=><div key={o.id}>{o.kind==='image'?<img src={o.url}/>:<div className="video-file"><Film/></div>}<section><b>{o.name}</b><span>{new Date(o.createdAt).toLocaleString('zh-CN')}</span></section><button onClick={()=>window.open(o.url)}><Download/></button></div>)}{!project.outputs?.length&&<div className="mini-empty"><Archive/><b>尚无可交付成果</b><span>先完成图片或视频生成。</span></div>}</div></div>
  </div>
}

function ComplianceCenter({ projects, openProject, onCreate }) {
  return <div className="page"><section className="hub-hero"><div className="hub-icon"><ShieldCheck size={28}/></div><div><span>发布前的最后一道门</span><h1>合规中心</h1><p>集中处理违禁词、绝对化表达、风险承诺与成果交付。</p></div></section><div className="compliance-overview"><div><strong>{projects.length}</strong><span>待管理项目</span></div><div><strong>{projects.reduce((s,p)=>s+(p.outputs?.length||0),0)}</strong><span>待检查成果</span></div><div><strong>14</strong><span>内置风险词组</span></div></div><div className="section-title compact"><div><span>PROJECT REVIEW</span><h2>选择项目开始检查</h2></div></div>{projects.length?<div className="list-stack">{projects.map(p=><button className="hub-project" key={p.id} onClick={()=>openProject(p.id,'review')}><div className="mini-cover"><ShieldCheck/></div><div><b>{p.name}</b><span>{p.outputs?.length||0} 项成果 · {p.status==='done'?'已交付':'制作中'}</span></div><div className="hub-stats"><span>内置规则初筛</span></div><ChevronRight/></button>)}</div>:<EmptyProjects onCreate={onCreate}/>}</div>
}

function SettingsPage({ health, notify }) {
  const [settings,setSettings]=useState(null); const [imageModels,setImageModels]=useState([]); const [videoModels,setVideoModels]=useState([]); const [busy,setBusy]=useState(false)
  useEffect(()=>{Promise.all([api('/api/settings'),api('/api/models?type=image'),api('/api/models?type=video')]).then(([s,i,v])=>{setSettings(s);setImageModels(i);setVideoModels(v)}).catch(e=>notify(e.message,'error'))},[])
  const save=async()=>{setBusy(true);try{setSettings(await api('/api/settings',{method:'PUT',body:JSON.stringify(settings)}));notify('模型配置已保存')}catch(e){notify(e.message,'error')}finally{setBusy(false)}}
  if(!settings)return <FullLoader/>
  return <div className="page settings-page"><PageHeading eyebrow="SYSTEM CONFIGURATION" title="模型与服务配置" desc="图片与视频使用 BOLI 实时模型别名；推理模型支持任意 OpenAI Compatible 服务。" action={<button className="button primary" onClick={save}>{busy?<LoaderCircle className="spin"/>:<Check/>}保存配置</button>}/>
    <div className="settings-grid"><div className="settings-nav"><button className="active"><BrainCircuit/>模型路由</button><button><Globe2/>搜索服务</button><button><Cloud/>素材网关</button><button><ShieldCheck/>安全策略</button></div><div className="settings-content">
      <div className="setting-card"><div className="setting-head"><div className="model-logo reasoning"><BrainCircuit/></div><div><b>推理 / 对话模型</b><span>用于全网信息总结、卖点提炼与脚本生成</span></div><em className={settings.reasoning.endpoint?'online':'optional'}>{settings.reasoning.endpoint?'已配置':'可选配置'}</em></div><div className="form-grid"><Field label="服务地址"><input value={settings.reasoning.endpoint} onChange={e=>setSettings({...settings,reasoning:{...settings.reasoning,endpoint:e.target.value}})} placeholder="https://api.example.com/v1"/></Field><Field label="模型名称"><input value={settings.reasoning.model} onChange={e=>setSettings({...settings,reasoning:{...settings.reasoning,model:e.target.value}})} placeholder="your-reasoning-model"/></Field><Field label="API Key"><input type="password" value={settings.reasoning.apiKey} onChange={e=>setSettings({...settings,reasoning:{...settings.reasoning,apiKey:e.target.value}})} placeholder="仅保存在本机服务端"/></Field><Field label="接口规范"><select><option>OpenAI Compatible</option></select></Field></div><p className="security-note"><ShieldCheck/>密钥不写入前端构建产物，也不会出现在应用日志中。未配置时使用本地结构化分析。</p></div>
      <div className="setting-card"><div className="setting-head"><div className="model-logo image"><Image/></div><div><b>图片生成模型</b><span>BOLI CLI 实时目录 · {imageModels.length} 个当前别名</span></div><em className="online">已连接</em></div><Field label="默认图片模型"><select value={settings.defaults.imageModel} onChange={e=>setSettings({...settings,defaults:{...settings.defaults,imageModel:e.target.value}})}><option value="">跟随实时推荐</option>{imageModels.map(m=><option key={m.id}>{m.id}</option>)}</select></Field><div className="model-chips">{imageModels.slice(0,6).map(m=><span key={m.id}>{m.name}</span>)}</div></div>
      <div className="setting-card"><div className="setting-head"><div className="model-logo video"><Video/></div><div><b>视频生成模型</b><span>BOLI CLI 实时目录 · {videoModels.length} 个当前别名</span></div><em className="online">已连接</em></div><Field label="默认视频模型"><select value={settings.defaults.videoModel} onChange={e=>setSettings({...settings,defaults:{...settings.defaults,videoModel:e.target.value}})}><option value="">跟随实时推荐</option>{videoModels.map(m=><option key={m.id}>{m.id}</option>)}</select></Field><div className="model-chips">{videoModels.slice(0,6).map(m=><span key={m.id}>{m.name}</span>)}</div></div>
      <div className="setting-card"><div className="setting-head"><div className="model-logo cloud"><Cloud/></div><div><b>公网素材网关</b><span>部署后让本地上传素材可作为参考图传递给生成模型</span></div></div><Field label="公开素材基础地址"><input value={settings.assetPublicBaseUrl} onChange={e=>setSettings({...settings,assetPublicBaseUrl:e.target.value})} placeholder="https://your-domain.com"/></Field></div>
      <div className="system-status"><div><span className="status-dot"/><b>BOLI 设备授权</b><small>{health?.ok?'图片与视频生成权限正常':'等待健康检查'}</small></div><div><b>{health?.boli?.balance?.toLocaleString?.()||'—'}</b><span>可用算力</span></div><div><b>{health?.boli?.operations?.filter(x=>x.available).length||0}</b><span>在线操作</span></div></div>
    </div></div>
  </div>
}

function CreateProjectModal({ platforms, onClose, onCreate }) {
  const [form,setForm]=useState({name:'',category:'',description:'',platform:'taobao',language:'zh-CN'}); const [busy,setBusy]=useState(false)
  const submit=async()=>{if(!form.name.trim())return;setBusy(true);try{await onCreate(form)}finally{setBusy(false)}}
  return <Modal onClose={onClose} className="create-modal"><div className="modal-kicker"><Box/>NEW PRODUCT PROJECT</div><h2>创建商品项目</h2><p className="modal-desc">每款商品拥有独立的素材、洞察、生成记录和交付成果。</p><div className="form-grid single"><Field label="商品名称 *"><input autoFocus value={form.name} onChange={e=>setForm({...form,name:e.target.value})} placeholder="例如：便携式无线榨汁杯"/></Field><Field label="商品品类"><input value={form.category} onChange={e=>setForm({...form,category:e.target.value})} placeholder="例如：厨房小家电"/></Field><Field label="商品简介"><textarea rows="3" value={form.description} onChange={e=>setForm({...form,description:e.target.value})} placeholder="材质、功能、目标人群、价格带或已有卖点…"/></Field><Field label="首发平台"><div className="platform-selector">{platforms.map(p=><button key={p.id} className={form.platform===p.id?'active':''} onClick={()=>setForm({...form,platform:p.id})}><i style={{background:p.accent}}/>{p.name}{form.platform===p.id&&<Check/>}</button>)}</div></Field><Field label="内容语言"><div className="language-selector"><button className={form.language==='zh-CN'?'active':''} onClick={()=>setForm({...form,language:'zh-CN'})}>中<span>简体中文</span></button><button className={form.language==='en-US'?'active':''} onClick={()=>setForm({...form,language:'en-US'})}>EN<span>English</span></button></div></Field></div><div className="modal-actions"><button className="button ghost" onClick={onClose}>取消</button><button className="button primary" disabled={!form.name.trim()||busy} onClick={submit}>{busy?<LoaderCircle className="spin"/>:<ArrowRight/>}创建并上传素材</button></div></Modal>
}

function Modal({children,onClose,className=''}) { return <div className="modal-backdrop" onMouseDown={e=>e.target===e.currentTarget&&onClose()}><div className={`modal ${className}`}><button className="modal-close" onClick={onClose}><X/></button>{children}</div></div> }
function PageHeading({eyebrow,title,desc,action}) { return <div className="page-heading"><div><span>{eyebrow}</span><h1>{title}</h1><p>{desc}</p></div>{action&&<div>{action}</div>}</div> }
function PanelTitle({icon:Icon,title,subtitle}) { return <div className="panel-title"><div><Icon size={18}/><b>{title}</b></div><span>{subtitle}</span></div> }
function Field({label,children}) { return <label className="field"><span>{label}</span>{children}</label> }
function FullLoader() { return <div className="full-loader"><div><Sparkles/><LoaderCircle className="spin"/></div><b>正在准备创作工作台</b><span>同步项目与模型能力…</span></div> }
function formatBytes(bytes){if(!bytes)return'0 B';const k=1024,i=Math.floor(Math.log(bytes)/Math.log(k));return`${(bytes/Math.pow(k,i)).toFixed(1)} ${['B','KB','MB','GB'][i]}`}
function defaultImagePrompt(project,tab,platform){const insight=project.insight;const common=`为商品“${project.name}”创作${platform?.name||'电商平台'}电商视觉，商品外观、结构、材质和品牌文字必须与参考素材一致；真实商业摄影质感，画面干净高级，主体突出，光影自然；内容语言：${project.language==='en-US'?'英文':'简体中文'}。核心卖点：${(insight?.sellingPoints||['结构细节清晰','使用场景直观','规格信息易读']).join('、')}。避免极限词、虚假承诺、错别字、乱码、水印和无关品牌。`;return tab==='main'?`${common}\n生成主图套装中的一张：一个清晰主题、一个主卖点、一处证据型标注，留出合理文案安全区。`:tab==='sku'?`${common}\n生成 SKU 规格展示图：统一视角和光线，清晰展示颜色/规格/组合差异，信息层级简洁。`:`${common}\n生成详情页模块：采用“痛点场景—核心方案—结构细节—使用步骤—规格参数—信任收口”的说服逻辑，适合纵向浏览。`}
function defaultVideoPrompt(project,type,platform){const sell=(project.insight?.sellingPoints||['外观细节','使用便利','场景价值']).slice(0,3);const base=`商品：${project.name}。目标平台：${platform?.name||'电商平台'}。保持商品外形、颜色、材质、结构稳定，不出现文字乱码、品牌变形、肢体畸形、物体穿模或空间跳变。`;if(type==='主图视频')return`${base}\n0-2秒：商品在干净场景中快速亮相，相机轻推近，环境声自然。\n2-6秒：用三个连续微距镜头展示${sell.join('、')}，每个镜头动作简洁。\n6-9秒：展示一次真实使用结果，主体始终清晰。\n9-10秒：定格商品英雄镜头，画面留出标题安全区。`;if(type==='操作视频')return`${base}\n0-2秒：展示商品和配件全貌。\n2-4秒：双手完成步骤一，动作慢而清楚。\n4-7秒：完成步骤二并展示正确姿势，镜头跟随关键部位。\n7-9秒：展示完成后的状态与结果。\n9-10秒：回到商品与使用结果同框，环境声和动作音效真实。`;return`${base}\n0-2秒：从用户常见痛点场景开场，动作自然，立即形成注意力。\n2-5秒：商品进入画面解决问题，连续动作展示核心功能。\n5-8秒：切到更理想的使用状态，呈现${sell.join('、')}。\n8-10秒：英雄镜头收口，视觉节奏有力，留出行动号召安全区。`}

export default App
