import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowUpRight, BookOpen, Check, ChevronRight, CircleHelp, Clock3, FileText, Folder, GitBranch, Layers3, ListChecks, RefreshCw, Search, ShieldCheck, X } from 'lucide-react';
import './ProjectOverview.css';
import BugPanel, { type BugData } from './project-overview/BugPanel';

type Feature = { id: string; title: string; kind: string; implementation: string; verification: string; verification_reason: string; task_ids: string[]; implementation_paths: string[]; requires: string[]; invariants: string[]; limitations: string[]; last_evidence: string | null; stage_evidence_refs: string[]; commits?: Commit[] };
type Commit = { commit: string; date: string; title: string };
type Task = { id: string; title: string; phase: string; status: string; note: string; depends_on: string[]; evidence_refs: string[]; previous_completion_claim?: { status: string }; implementation_steps: string[]; source: string };
type Handoff = { task_id: string; session_id: string; created_at: string; summary: string; next_action: string; completed: string[]; pending: string[]; decisions: string[]; failed_approaches: string[]; evidence_refs: string[]; path: string; commit: string; features: { id: string; basis: string }[] };
type Report = { path: string; date: string; overall: string; features: string[]; application_executed: boolean; live_model_called: boolean; results: { id: string; status: string; exit_code: number; tests?: number }[] };
type Entry = { path: string; name: string; description: string; description_source: string; is_dir: boolean; readable: boolean; expandable: boolean; restricted: boolean; size: number | null; features: string[] };
type Tree = { path: string; entries: Entry[]; total: number; next_offset: number | null; offset: number };
type Reference = Pick<Entry, 'path' | 'description' | 'is_dir' | 'readable' | 'expandable'> & { label: string };
type Snapshot = { bugs: BugData; generated_at: string; branch: string; head: string; stage: string; next_task: string; versions: { bundle: string; product: string; frontend: string }; features: Feature[]; tasks: Task[]; handoffs: Handoff[]; reports: Report[]; commits: Commit[]; references: Reference[]; warnings: string[]; directories: { path: string; description: string; expandable: boolean }[] };
type Section = 'features' | 'tasks' | 'guide' | 'files' | 'bugs';
const labels: Record<string, string> = { IMPLEMENTED: '已实现', IN_PROGRESS: '进行中', NOT_STARTED: '未开始', DEPRECATED: '已停用', DONE: '已完成', BLOCKED: '受阻', OFFLINE_PASS: '离线验证通过', NOT_RUN: '尚无验收记录', STAGE_RECORDS: '已有阶段验证记录', STALE: '证据已过期', FAILED: '验证失败', FAIL: '失败', PASS: '报告通过', INVALID: '证据不可核对', INCOMPLETE: '验证不完整', RUNNING: '运行中', PRODUCT: '产品功能', DEVTOOL: '开发工具' };
const nav = [{ id: 'bugs' as const, label: 'Bug 记录', icon: ShieldCheck }, { id: 'features' as const, label: '功能与迭代', icon: Layers3 }, { id: 'tasks' as const, label: '任务与验收', icon: ListChecks }, { id: 'guide' as const, label: '开发规则导航', icon: BookOpen }, { id: 'files' as const, label: '目录与文件', icon: Folder }];
const formatDate = (s: string) => s ? new Date(s).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '未登记时间';
async function read<T>(mode: string, params: Record<string, string> = {}): Promise<T> {
  const response = await fetch(`/__project/${mode}?${new URLSearchParams(params)}`);
  if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) throw new Error('项目资料读取失败。请使用本机 Vite 开发服务，并检查项目 Python 环境与记录文件。');
  const result = await response.json();
  if (result.error) throw new Error(result.error);
  return result;
}
const displayedVerification = (feature: Feature) => feature.verification === 'NOT_RUN' && feature.stage_evidence_refs?.length ? 'STAGE_RECORDS' : feature.verification;
function Badge({ value }: { value: string }) { return <span className={`po-badge po-${value.toLowerCase()}`}>{labels[value] || value}</span>; }
function Notes({ items, empty = '暂无登记。' }: { items: string[]; empty?: string }) { return items?.length ? <ul className="po-notes">{items.map((v, i) => <li key={i}>{v}</li>)}</ul> : <p className="po-muted">{empty}</p>; }

/** Basic document typography; text stays escaped, no HTML execution. */
function DocumentText({ content, path }: { content: string; path: string }) {
  if (!path.endsWith('.md')) return <pre className="po-source">{content}</pre>;
  const lines = content.split('\n'); const blocks = []; let i = 0;
  while (i < lines.length) {
    const line = lines[i++];
    if (line.startsWith('```')) { const code = []; while (i < lines.length && !lines[i].startsWith('```')) code.push(lines[i++]); i++; blocks.push(<pre key={i}>{code.join('\n')}</pre>); }
    else if (line.startsWith('|')) { const rows = [line]; while (i < lines.length && lines[i].startsWith('|')) rows.push(lines[i++]); blocks.push(<div className="po-table-scroll" key={i}><table><tbody>{rows.filter(r => !/^\|[\s:|\-]+$/.test(r)).map((r, j) => <tr key={j}>{r.split('|').slice(1, -1).map((c, k) => j === 0 ? <th key={k}>{c.trim()}</th> : <td key={k}>{c.trim()}</td>)}</tr>)}</tbody></table></div>); }
    else if (/^#{1,6} /.test(line)) blocks.push(<h3 key={i}>{line.replace(/^#+ /, '')}</h3>);
    else if (line.startsWith('>')) blocks.push(<blockquote key={i}>{line.replace(/^> ?/, '')}</blockquote>);
    else if (line.trim()) blocks.push(<p key={i}>{line}</p>);
  }
  return <article className="po-document-text">{blocks}</article>;
}

export default function ProjectOverview() {
  const [data, setData] = useState<Snapshot | null>(null);
  const [error, setError] = useState(''); const [loading, setLoading] = useState(true);
  const [section, setSection] = useState<Section>(new URLSearchParams(window.location.search).get('tab') === 'bugs' ? 'bugs' : 'features'); const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('ALL'); const [selected, setSelected] = useState('');
  const [detailTab, setDetailTab] = useState<'scope' | 'history'>('scope');
  const [directory, setDirectory] = useState(''); const [tree, setTree] = useState<Tree | null>(null);
  const [treeError, setTreeError] = useState(''); const [treeLoading, setTreeLoading] = useState(false);
  const [treeVersion, setTreeVersion] = useState(0);
  const [offset, setOffset] = useState(0); const [fileQuery, setFileQuery] = useState(''); const [entry, setEntry] = useState<Entry | null>(null);
  const [doc, setDoc] = useState<{ path: string; content: string; notice: string } | null>(null); const [docError, setDocError] = useState('');
  const detail = useRef<HTMLElement>(null);
  const dialog = useRef<HTMLDialogElement>(null); const treeRequest = useRef(0);
  async function refresh() {
    setLoading(true); setError('');
    try { const value = await read<Snapshot>('snapshot'); setData(value); setSelected(s => s || value.features[0]?.id || ''); }
    catch (e) { setError((e as Error).message); }
    finally { setLoading(false); }
  }
  useEffect(() => { document.title = '知卷 · 项目进展与开发资料'; void refresh(); }, []);
  useEffect(() => {
    if (section !== 'files') return;
    const current = ++treeRequest.current; setTreeLoading(true); setTreeError('');
    const timer = window.setTimeout(() => {
      void read<Tree>('tree', { path: directory, offset: String(offset), query: fileQuery }).then(t => { if (current === treeRequest.current) setTree(t); }).catch(e => { if (current === treeRequest.current) setTreeError(e.message); }).finally(() => { if (current === treeRequest.current) setTreeLoading(false); });
    }, 120);
    return () => { clearTimeout(timer); treeRequest.current++; };
  }, [directory, offset, fileQuery, section, treeVersion]);
  useEffect(() => { if (doc && !dialog.current?.open) dialog.current?.showModal(); }, [doc]);
  function changeSection(next: Section) { setSection(next); setQuery(''); setFilter('ALL'); }
  function browse(path = '') { changeSection('files'); setDirectory(path); setOffset(0); setFileQuery(''); setEntry(null); }
  function pathLink(path: string) {
    const clean = path.replace(/\/\*.*$/, '');
    if (!clean.split('/').pop()?.includes('.')) browse(clean);
    else { browse(clean.includes('/') ? clean.slice(0, clean.lastIndexOf('/')) : ''); setFileQuery(clean.split('/').pop() || ''); }
  }
  async function openDocument(path: string) {
    setDocError(''); setDoc({ path, content: '正在读取…', notice: '' });
    try { setDoc(await read('document', { path })); }
    catch (e) { setDoc(null); dialog.current?.close(); setDocError((e as Error).message); }
  }
  const feature = data?.features.find(f => f.id === selected);
  const history = data?.handoffs.filter(h => h.features.some(f => f.id === selected)) || [];
  const filtered = data?.features.filter(f => (filter === 'ALL' || f.implementation === filter) && `${f.id} ${f.title} ${f.limitations.join(' ')}`.toLowerCase().includes(query.toLowerCase())) || [];
  const latestCheckpoint = data?.handoffs.find(h => feature?.task_ids.includes(h.task_id));
  const products = data?.features.filter(f => f.kind === 'PRODUCT') || [];
  const count = (status: string) => products.filter(f => f.implementation === status).length;
  useEffect(() => {
    if (section === 'features') setSelected(current => filtered.some(f => f.id === current) ? current : filtered[0]?.id || '');
  }, [data, filter, query, section]);
  function selectFeature(id: string) {
    setSelected(id); setDetailTab('scope');
    if (window.matchMedia('(max-width: 800px)').matches) requestAnimationFrame(() => detail.current?.scrollIntoView({ block: 'start' }));
  }
  const PathButton = ({ path }: { path: string }) => <button className="po-path" onClick={() => pathLink(path)}>{path}<ArrowUpRight size={12}/></button>;

  return <div className="po-shell">
    <aside className="po-sidebar">
      <a className="po-brand" href="/"><span className="po-brand-mark">知</span><span>知卷<span className="po-brand-sub">PROJECT WORKSPACE</span></span></a>
      <div className="po-workspace-label">开发工作台 <span>LOCAL</span></div>
      <nav aria-label="项目资料导航">{nav.map(n => <button key={n.id} aria-current={section === n.id ? 'page' : undefined} className={section === n.id ? 'active' : ''} onClick={() => changeSection(n.id)}><n.icon size={18}/>{n.label}{section === n.id && <ChevronRight size={16}/>}</button>)}</nav>
      <div className="po-sidebar-bottom"><span className="po-dot"/>直接读取本地账本<p>每条状态都有来源。<br/>历史声明与验收结果分开展示。</p><a href="/"><ArrowLeft size={14}/>返回教师工作台</a></div>
    </aside>
    <main className="po-main">
      <header className="po-topbar"><div><span className="po-muted">知卷项目</span><ChevronRight size={14}/><strong>{nav.find(n => n.id === section)?.label}</strong></div><div><span className="po-branch"><GitBranch size={14}/>{data?.branch || '本地仓库'}</span><button className="po-icon-button" aria-label="刷新项目数据" disabled={loading} onClick={() => { void refresh(); setTreeVersion(v => v + 1); }}><RefreshCw size={16} className={loading ? 'po-spin' : ''}/></button></div></header>
      <div className="po-content">
        <div className="po-page-title"><div><span className="po-eyebrow">ZHIJUAN / PROJECT AT A GLANCE</span><h1>{section === 'bugs' ? '让修过的问题，成为下次的线索' : section === 'features' ? '项目做到哪一步了？' : section === 'tasks' ? '从开发任务，到验收证据' : section === 'guide' ? '把开发约定，变成可读的地图' : '每个目录，各司其职'}</h1><p>{section === 'bugs' ? '记录症状、根因、修复与回归；复发时延续原记录。' : section === 'features' ? '看清已做的、还缺的，以及每一次迭代留下的依据。' : section === 'tasks' ? '原始计划保留，实际进度覆盖；测试报告始终说明它验证了什么。' : section === 'guide' ? 'AGENTS.md 是入口；功能、任务、报告与交接各自维护一种事实。' : '逐级浏览全部目录和文件，查看中文用途、关联功能及可阅读文档。'}</p></div><span className="po-readonly"><ShieldCheck size={14}/>本地 · 只读</span></div>
        {error && <div className="po-error" role="alert">{error}<button onClick={() => void refresh()}>重试</button></div>}
        {docError && <div className="po-error" role="alert">{docError}</div>}
        {loading && !data && <div className="po-empty" role="status"><RefreshCw className="po-spin"/>正在整理账本、交接与证据…</div>}
        {data?.warnings.map(w => <div className="po-warning" key={w}>{w}</div>)}
        {data && <>
          {section === 'bugs' && <BugPanel data={data.bugs || { items: [], database_url: '' }} openDocument={path => void openDocument(path)} />}
          {section === 'features' && <>
            <section className="po-overview"><div className="po-progress-summary"><span className="po-eyebrow">当前阶段 / {data.stage}</span><h2>{count('IMPLEMENTED') ? `已实现 ${count('IMPLEMENTED')} 项产品功能` : '核心功能持续开发中'}</h2><p>产品功能 {products.length} 项 · 开发工具 {data.features.length - products.length} 项</p><div className="po-segments" aria-label={`${count('IMPLEMENTED')}项已实现，${count('IN_PROGRESS')}项进行中，${count('NOT_STARTED')}项未开始`}>{products.map(f => <span key={f.id} className={`po-segment-${f.implementation.toLowerCase()}`} title={`${f.title}：${labels[f.implementation]}`}/>)}</div><div className="po-legend"><span><i className="is-built"/>{count('IMPLEMENTED')} 已实现</span><span><i className="is-progress"/>{count('IN_PROGRESS')} 进行中</span><span><i/>{count('NOT_STARTED')} 未开始</span></div></div><div className="po-next"><span className="po-eyebrow">下一步建议</span><div className="po-next-id">{data.next_task}<ArrowUpRight size={20}/></div><p>{data.tasks.find(t => t.id === data.next_task)?.title}</p><button onClick={() => {changeSection('tasks');setQuery(data.next_task);}}>查看任务与前置依赖 <ChevronRight size={14}/></button></div></section>
            <div className="po-evidence-note"><CircleHelp size={16}/><span><strong>已实现 ≠ 已验收。</strong> 这里展示账本状态，不把离线测试、历史总结或模拟进度当作产品验收。</span><button onClick={() => changeSection('guide')}>如何理解这些记录？</button></div>
            <div className="po-toolbar"><div className="po-filters" aria-label="功能状态筛选">{[['ALL','全部功能'],['IMPLEMENTED','已实现'],['IN_PROGRESS','进行中'],['NOT_STARTED','未开始']].map(([v,l]) => <button key={v} className={filter===v?'active':''} aria-pressed={filter===v} onClick={()=>setFilter(v)}>{l}</button>)}</div><label className="po-search"><Search size={16}/><input aria-label="搜索功能" placeholder="搜索功能或关键词" value={query} onChange={e=>setQuery(e.target.value)}/></label></div>
            <div className="po-feature-layout"><div className="po-feature-list">{filtered.length === 0 && <div className="po-empty">没有匹配的功能，试试其他关键词。</div>}{filtered.map(f=><button key={f.id} onClick={()=>selectFeature(f.id)} aria-pressed={selected===f.id} className={`po-feature-card ${selected===f.id?'selected':''}`}><div className="po-card-top"><span className="po-mono">{f.id.replace('FEAT-','')}</span><Badge value={f.implementation}/></div><h3>{f.title}</h3><p>{f.kind==='DEVTOOL'?'开发工具':'产品功能'} · {f.task_ids.length} 个关联任务</p><div className="po-card-bottom"><span className={`po-verification po-${f.verification.toLowerCase()}`}>{f.verification==='OFFLINE_PASS'?<Check size={13}/>:<Clock3 size={13}/>} {labels[displayedVerification(f)] || f.verification}</span><ChevronRight size={15}/></div></button>)}</div>
            {feature && <section ref={detail} className="po-detail" aria-label="功能详情"><div className="po-detail-heading"><span className="po-eyebrow">{feature.id} / {labels[feature.kind]}</span><h2>{feature.title}</h2><div className="po-badges"><Badge value={feature.implementation}/><Badge value={displayedVerification(feature)}/></div></div><div className="po-detail-tabs"><button className={detailTab==='scope'?'active':''} onClick={()=>setDetailTab('scope')}>当前情况</button><button className={detailTab==='history'?'active':''} onClick={()=>setDetailTab('history')}>迭代记录 <span>{history.length}</span></button></div>
              {detailTab==='scope'?<div className="po-detail-body"><h4>当前实现与限制</h4><Notes items={feature.limitations}/>{latestCheckpoint && <><h4>最近一次开发更新</h4><p>{formatDate(latestCheckpoint.created_at)} · {latestCheckpoint.task_id}</p><p>{latestCheckpoint.summary}</p><h5>本次已做</h5><Notes items={latestCheckpoint.completed}/><h5>还需完成</h5><Notes items={latestCheckpoint.pending}/></>}<h4>验证依据</h4>{feature.stage_evidence_refs?.length > 0 && <><p>已登记 {feature.stage_evidence_refs.length} 份阶段验证资料，来自关联任务及交接。只证明各次记录的范围，历史报告可能已过期。</p><details><summary>查看阶段验证资料</summary>{feature.stage_evidence_refs.map(p=><PathButton key={p} path={p}/>)}</details></>}<p className="po-muted">{feature.verification === 'NOT_RUN' ? (feature.stage_evidence_refs?.length ? '完整功能验收尚未完成，当前继续保持“进行中”。上方的阶段验证记录不会自动将整个功能标为完成。' : '尚无登记的功能验收报告。') : feature.verification_reason}</p>{feature.last_evidence && <PathButton path={feature.last_evidence}/>}<h4>已经落到哪些文件</h4>{feature.implementation_paths.length?feature.implementation_paths.map(p=><PathButton key={p} path={p}/>):<p className="po-muted">尚无登记的实现入口。</p>}<h4>关联任务</h4><div className="po-chips">{feature.task_ids.map(id=><button key={id} onClick={()=>{changeSection('tasks');setQuery(id);}}>{id}<ArrowUpRight size={12}/></button>)}</div><h4>依赖功能</h4><div className="po-chips">{feature.requires.length?feature.requires.map(id=><button key={id} onClick={()=>{setFilter('ALL');setQuery('');selectFeature(id);}}>{data.features.find(f=>f.id===id)?.title || id}</button>):<span className="po-muted">无前置功能登记</span>}</div><h4>不能破坏的行为</h4><Notes items={feature.invariants}/><div className="po-source-foot">数据来源 <button onClick={()=>void openDocument('progress/features.yaml')}>progress/features.yaml</button></div></div>:<div className="po-detail-body"><div className="po-warning">以下是关联开发检查点，不是正式发布版本；交接中的“已完成”仍需对照当前限制与证据。</div>{history.length===0 && <p className="po-empty">尚无关联检查点，暂不推断迭代版本。</p>}<div className="po-timeline">{history.map(h=><article key={h.path}><time>{formatDate(h.created_at)} · {h.task_id}</time><h4>{h.summary}</h4><span className="po-mono">{h.session_id}</span><p className="po-muted">{h.features.find(f=>f.id===selected)?.basis}</p><details><summary>展开已做、待办与证据</summary><h5>交接记载的已做事项</h5><Notes items={h.completed}/><h5>待办</h5><Notes items={h.pending}/><h5>决策与失败尝试</h5><Notes items={[...(h.decisions || []),...(h.failed_approaches || [])]}/><h5>下一动作</h5><p>{h.next_action}</p><h5>证据路径</h5>{h.evidence_refs.map(p=><PathButton key={p} path={p}/>)}<p className="po-muted">记录时 HEAD：{h.commit?.slice(0,12)||'未登记'}；不证明改动已提交。</p><PathButton path={h.path}/></details></article>)}</div><h4>关联源码提交</h4><p className="po-muted">按登记实现路径查询 Git；未提交改动不出现在这里。</p>{feature.commits?.length?feature.commits.map(c=><p key={c.commit}><code>{c.commit.slice(0,7)}</code> {c.title}<small className="po-muted"> · {formatDate(c.date)}</small></p>):<p className="po-muted">暂无可关联的提交记录。</p>}</div>}
            </section>}</div>
          </>}
          {section==='tasks' && <>
            <div className="po-toolbar"><div className="po-filters">{['ALL','M0','M1','M2','M3'].map(v=><button key={v} className={filter===v?'active':''} onClick={()=>setFilter(v)}>{v==='ALL'?'全部阶段':v}</button>)}</div><label className="po-search"><Search size={16}/><input aria-label="搜索任务" placeholder="任务编号 / 标题" value={query} onChange={e=>setQuery(e.target.value)}/></label></div>
            <div className="po-task-list">{data.tasks.filter(t=>(filter==='ALL'||filter===t.phase)&&`${t.id} ${t.title}`.toLowerCase().includes(query.toLowerCase())).map(t=><details key={t.id} className="po-task"><summary><span className="po-mono">{t.id}</span><strong>{t.title}</strong><Badge value={t.status}/><ChevronRight size={16}/></summary><div className="po-task-body"><p>{t.note || '暂无额外说明。'}</p>{t.previous_completion_claim && <div className="po-warning">曾登记为 {t.previous_completion_claim.status}，现已根据证据纠正；历史声明保留，当前状态以上方为准。</div>}<h4>前置任务</h4><div className="po-chips">{t.depends_on.length?t.depends_on.map(id=><button key={id} onClick={()=>{setFilter('ALL');setQuery(id);}}>{id} · {labels[data.tasks.find(d=>d.id===id)?.status||'NOT_STARTED']}</button>):'无'}</div><h4>任务要求</h4><Notes items={t.implementation_steps}/><h4>登记依据（路径存在不等于已验收）</h4>{t.evidence_refs.map(p=><PathButton key={p} path={p}/>)}<p className="po-muted">状态来源：{t.source}</p></div></details>)}</div>
            <div className="po-section-heading"><h2>已有运行报告</h2><span>历史报告不会自动升级为当前证据</span></div><div className="po-report-grid">{data.reports.map(r=><details key={r.path} className="po-report"><summary><Badge value={r.overall}/><strong>{r.path.split('/').slice(-2,-1)[0]}</strong><span>{formatDate(r.date)}</span></summary><div className="po-task-body"><p>应用执行：{r.application_executed?'报告记载已执行':'未执行'} · 模型调用：{r.live_model_called?'报告记载已调用':'未调用'}</p>{r.results.map((v,i)=><div className="po-report-row" key={i}><span>{v.id}{v.tests ? ` · ${v.tests} 项测试` : ''}</span><Badge value={v.status}/></div>)}<PathButton path={r.path}/></div></details>)}</div>
          </>}
          {section==='guide' && <>
            <section className="po-guide-intro"><div><span className="po-eyebrow">先看这五种资料</span><h2>计划、实现、证据，各有归属。</h2><p>不需要再从一堆 YAML 和 Markdown 中猜进度。先选你要回答的问题，再进入对应的事实来源。</p></div><button className="po-primary" onClick={()=>void openDocument('AGENTS.md')}>阅读当前 AGENTS.md <ArrowUpRight size={16}/></button></section>
            <div className="po-explain-grid">{[['功能实现','到底做出了什么？','progress/features.yaml','实现入口、依赖与限制。已实现也可能还没验收。'],['任务进度','这一项工作做完了吗？','progress/work.yaml','覆盖旧计划的实际状态，包含纠正原因。'],['验收证据','靠什么证明做完了？','acceptance-runs','一次运行的结果，只覆盖当次环境与范围。'],['迭代交接','上次改了什么？','progress/handoffs','历史工作声明、待办、决定与失败尝试。'],['自动摘要','现在整体在哪一步？','progress/current.md','账本生成的阅读入口，不单独维护状态。']].map(([title,question,path,desc])=><button key={path} onClick={()=>path.endsWith('.yaml')||path.endsWith('.md')?void openDocument(path):browse(path)} className="po-explain-card"><span>{title}</span><h3>{question}</h3><p>{desc}</p><code>{path}</code><ArrowUpRight size={16}/></button>)}</div>
            <div className="po-section-heading"><h2>AGENTS.md 引用导航</h2><span>动态提取链接与现有路径 · {data.references.length} 个入口</span></div><div className="po-reference-list">{data.references.map(r=><button key={r.path} onClick={()=>r.readable?void openDocument(r.path):browse(r.path)} disabled={!r.readable&&!r.expandable}><span className="po-file-icon">{r.is_dir?<Folder size={20}/>:<FileText size={20}/>}</span><span><strong>{r.label}</strong><p>{r.description}</p><code>{r.path}</code></span><ArrowUpRight size={16}/></button>)}</div>
            <div className="po-section-heading"><h2>版本应该怎么理解？</h2></div><div className="po-version-grid"><div><span>产品方案基线</span><strong>v{data.versions.product}</strong><p>需求与接口约定的版本</p></div><div><span>交接包版本</span><strong>v{data.versions.bundle}</strong><p>开发记录机制的交付版本</p></div><div><span>前端包版本</span><strong>{data.versions.frontend}</strong><p>package.json 声明，不是验收结论</p></div></div><p className="po-muted">单个功能未维护独立发布版本时，以关联检查点和源码提交追踪；不自动为它编号 v1 / v2。</p>
          </>}
          {section==='files' && <>
            <div className="po-file-layout"><aside className="po-directory-list"><button className={directory===''?'active':''} onClick={()=>browse('')}>全部根目录</button>{data.directories.map(d=><button title={d.description} key={d.path} disabled={!d.expandable} className={directory===d.path || directory.startsWith(d.path+'/')?'active':''} onClick={()=>browse(d.path)}><Folder size={15}/><span>{d.path}</span>{!d.expandable&&<span className="po-lock">受限</span>}</button>)}</aside><section className="po-file-panel"><div className="po-file-toolbar"><div className="po-breadcrumb"><button onClick={()=>browse('')}>知卷</button>{directory.split('/').filter(Boolean).map((v,i,a)=><span key={i}><ChevronRight size={13}/><button onClick={()=>browse(a.slice(0,i+1).join('/'))}>{v}</button></span>)}</div><label className="po-search"><Search size={15}/><input aria-label="筛选当前目录文件" placeholder="筛选当前目录文件名" value={fileQuery} onChange={e=>{setFileQuery(e.target.value);setOffset(0);}}/></label></div>
              <div className="po-file-note">目录与文件逐级完整列出；未知用途标为推断。依赖、凭据和缓存仅显示说明，上传资料、教材与日志不提供正文。</div>{treeError && <div className="po-error" role="alert">{treeError}</div>}{treeLoading?<div className="po-empty" role="status">正在读取目录…</div>:tree && <><div className="po-file-list">{tree.entries.length===0&&<div className="po-empty">此目录没有匹配的文件。</div>}{tree.entries.map(e=><button key={e.path} className={`po-file-row ${entry?.path===e.path?'selected':''}`} onClick={()=>e.expandable?browse(e.path):setEntry(e)}><span className="po-file-icon">{e.is_dir?<Folder size={20}/>:<FileText size={20}/>}</span><span><strong>{e.name}</strong><p>{e.description}</p></span><span className="po-file-meta">{e.restricted?'受限':e.description_source}<small>{e.is_dir?'目录':e.size!==null?`${(e.size/1024).toFixed(1)} KB`:''}</small></span><ChevronRight size={15}/></button>)}</div><div className="po-pagination"><span>{tree.total} 项 · {tree.total?tree.offset+1:0}–{Math.min(tree.offset+150,tree.total)}</span><button disabled={tree.offset===0} onClick={()=>setOffset(Math.max(0,offset-150))}>上一页</button><button disabled={tree.next_offset===null} onClick={()=>setOffset(tree.next_offset||0)}>下一页</button></div></>}
              {entry&&<div className="po-file-detail"><div><h3>{entry.name}</h3><button aria-label="关闭文件详情" onClick={()=>setEntry(null)}><X size={16}/></button></div><code>{entry.path}</code><p>{entry.description}</p><small>说明依据：{entry.description_source}</small>{data.handoffs.filter(h=>h.path===entry.path).map(h=><section className="po-record-preview" key={h.path}><h4>交接摘要 · {formatDate(h.created_at)}</h4><p>{h.summary}</p><h4>交接记载的已做事项</h4><Notes items={h.completed}/><h4>仍需完成</h4><Notes items={h.pending}/><h4>下一动作</h4><p>{h.next_action}</p><p className="po-muted">历史声明不等于当前验收结论。</p></section>)}{data.reports.filter(r=>r.path===entry.path).map(r=><section className="po-record-preview" key={r.path}><h4>报告摘要</h4><Badge value={r.overall}/><p>应用执行：{r.application_executed?'报告记载已执行':'未执行'} · 模型调用：{r.live_model_called?'报告记载已调用':'未调用'}</p>{r.results.map((v,i)=><div key={i} className="po-report-row"><span>{v.id}{v.tests?` · ${v.tests} 项测试`:''}</span><Badge value={v.status}/></div>)}</section>)}<div className="po-chips">{entry.features.map(id=><button key={id} onClick={()=>{changeSection('features');setSelected(id);}}>{data.features.find(f=>f.id===id)?.title || id}<ArrowUpRight size={12}/></button>)}</div>{entry.readable?<button className="po-primary" onClick={()=>void openDocument(entry.path)}>阅读文档 <BookOpen size={14}/></button>:<p className="po-muted">本页仅展示此文件的用途和关联信息，不读取其正文。</p>}</div>}
            </section></div>
          </>}
          <footer className="po-footer"><span><span className="po-dot"/>读取于 {formatDate(data.generated_at)} · 点击右上角刷新获取最新记录</span><span>HEAD {data.head.slice(0,8) || '—'} · 只读工作区</span></footer>
        </>}
      </div>
    </main>
    <dialog ref={dialog} className="po-document-dialog" onCancel={()=>setDoc(null)} onClose={()=>setDoc(null)}><div className="po-dialog-heading"><div><span className="po-eyebrow">源文档 / 只读</span><h2>{doc?.path}</h2></div><button aria-label="关闭文档" onClick={()=>{dialog.current?.close();setDoc(null);}}><X size={20}/></button></div><p className="po-dialog-notice">{doc?.notice}</p>{doc&&<DocumentText content={doc.content} path={doc.path}/>}</dialog>
  </div>;
}
