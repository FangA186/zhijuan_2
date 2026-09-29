import { useState } from 'react';
import './BugPanel.css';

export type BugRecord = {
  id: string; title: string; status: string; module: string; keywords: string[];
  task_ids: string[]; symptom: string; reproduction: string[]; root_cause: string;
  resolution: string; affected_files: string[]; regression: string[]; evidence_refs: string[];
  events: string[]; path: string; verified_at: string; verification: string;
  notion_url: string; sync_status: string; source_state: string; evidence_available: boolean;
};
export type BugData = { items: BugRecord[]; database_url: string };
const labels: Record<string, string> = { OPEN: '待处理', FIXED: '已修复', REOPENED: '复发' };

export default function BugPanel({ data, openDocument }: {
  data: BugData; openDocument: (path: string) => void;
}) {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('ALL');
  const [selected, setSelected] = useState('');
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const visible = data.items.filter(bug => (status === 'ALL' || bug.status === status)
    && words.every(word => JSON.stringify(bug).toLowerCase().includes(word)));
  const current = visible.find(bug => bug.id === selected) || visible[0];
  return <section aria-label="Bug 记录" className="po-bugs">
    <div className="po-evidence-note">
      <span><strong>先查旧问题，再修当前问题。</strong> 按症状、报错、文件路径或任务 ID 搜索。
        已修复是历史结论，复用前仍需核对当前代码和失败复现。</span>
    </div>
    <div className="po-bug-summary">
      {Object.entries(labels).map(([key, label]) => <button key={key}
        onClick={() => setStatus(key)} aria-pressed={status === key}>
        <strong>{data.items.filter(bug => bug.status === key).length}</strong>{label}
      </button>)}
      <span>{data.items.filter(bug => bug.sync_status !== '已同步').length} 条待同步 Notion</span>
      {data.database_url && <a href={data.database_url} target="_blank" rel="noreferrer">打开 Notion Bug 库 ↗</a>}
    </div>
    <div className="po-toolbar">
      <div className="po-filters" aria-label="Bug 状态筛选">
        {Object.entries({ ALL: '全部', ...labels }).map(([key, label]) =>
          <button key={key} aria-pressed={status === key} className={status === key ? 'active' : ''}
            onClick={() => setStatus(key)}>{label}</button>)}
      </div>
      <label className="po-search"><input aria-label="搜索 Bug" placeholder="症状、报错、路径、任务 ID"
        value={query} onChange={event => setQuery(event.target.value)} /></label>
    </div>
    <p className="po-muted" role="status">匹配 {visible.length} 条记录</p>
    <div className="po-bug-layout">
      <div className="po-bug-list">
        {visible.map(bug => <button key={bug.id} className={current?.id === bug.id ? 'selected' : ''}
          aria-pressed={current?.id === bug.id} onClick={() => setSelected(bug.id)}>
          <span className="po-mono">{bug.id} · {labels[bug.status]}</span>
          <h3>{bug.title}</h3><p>{bug.module} · {bug.task_ids.join(' / ')}</p>
          <small>{bug.sync_status} · {bug.source_state}</small>
        </button>)}
        {!visible.length && <p className="po-empty">没有匹配的 Bug，换用报错关键词或模块名称。</p>}
      </div>
      {current && <article className="po-detail po-bug-detail" aria-label="Bug 详情">
        <span className="po-eyebrow">{current.id} · {labels[current.status]}</span>
        <h2>{current.title}</h2><p className="po-muted">{current.verified_at || '尚未验证'} · {current.verification || 'NOT_RUN'}</p>
        <p className="po-warning">{current.source_state}；文件指纹一致也不等于当前验收通过。</p>
        {!current.evidence_available && <p role="alert">记录引用的证据文件缺失，需重新核对。</p>}
        <h3>症状</h3><p>{current.symptom}</p>
        <h3>复现条件</h3><ul>{current.reproduction.map((v, i) => <li key={i}>{v}</li>)}</ul>
        <h3>根因</h3><p>{current.root_cause || '待查明'}</p>
        <h3>修复方法</h3><p>{current.resolution || '尚未修复'}</p>
        <h3>代码位置</h3><ul>{current.affected_files.map(v => <li key={v}><code>{v}</code></li>)}</ul>
        <h3>回归方式</h3><ul>{current.regression.map((v, i) => <li key={i}><code>{v}</code></li>)}</ul>
        <h3>验证证据</h3><ul>{current.evidence_refs.map(v => <li key={v}><code>{v}</code></li>)}</ul>
        <h3>发生与修复历史</h3><ul>{current.events.map((v, i) => <li key={i}>{v}</li>)}</ul>
        <div className="po-bug-links">
          <button className="po-primary" onClick={() => openDocument(current.path)}>打开本地记录</button>
          {current.notion_url && <a href={current.notion_url} target="_blank" rel="noreferrer">在 Notion 查看 ↗</a>}
        </div>
      </article>}
    </div>
  </section>;
}
