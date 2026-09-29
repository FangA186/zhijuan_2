import { useEffect, useRef, useState } from 'react';
import { Activity, ArrowDown, Copy } from 'lucide-react';
import type { JobEventLog } from '../../types/job';

import { activityText, activityTitle, timelineLogs } from './activityPresentation';
const roles: Record<string, string> = { planner: '规划', author: '命题', solver: '盲解', reviewer: '审核', system: '系统' };
interface Props { logs: JobEventLog[]; terminal: boolean; status: string; }

export function AgentActivityConsole({ logs, terminal, status }: Props) {
  const [role, setRole] = useState('all');
  const [follow, setFollow] = useState(true);
  const [copyNote, setCopyNote] = useState('');
  const panel = useRef<HTMLDivElement>(null);
  const visible = timelineLogs(logs).filter(log => role === 'all' || log.role === role);
  const hasOutput = logs.some(log => log.kind);
  useEffect(() => {
    if (follow && panel.current) panel.current.scrollTop = panel.current.scrollHeight;
  }, [logs, follow]);
  const copy = async () => {
    try { await navigator.clipboard.writeText(JSON.stringify(visible, null, 2)); setCopyNote('已复制'); }
    catch { setCopyNote('复制失败，请选中文本复制'); }
  };
  return <section className="min-w-0 overflow-hidden rounded-2xl border border-white/10 bg-[#161616] text-slate-100 shadow-md" aria-label="Agent 实时输出">
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-4 py-3">
      <div className="flex items-center gap-2"><Activity size={16} className="text-emerald-400" /><h3 className="font-semibold text-sm">Agent 实时输出</h3></div>
      <span className="text-xs text-slate-400">{terminal ? '执行已结束 · 可回看' : '正在接收事件'}</span>
    </header>
    <div className="flex flex-wrap items-center gap-3 px-4 py-2 border-b border-white/10 text-xs">
      <select aria-label="筛选执行角色" value={role} onChange={e => setRole(e.target.value)} className="bg-slate-900 border border-slate-600 rounded px-2 py-1">
        <option value="all">全部角色</option>{Object.entries(roles).map(([value, name]) => <option key={value} value={value}>{name}</option>)}
      </select>
      <label className="flex items-center gap-1.5"><input type="checkbox" checked={follow} onChange={e => setFollow(e.target.checked)} />自动跟随</label>
      <button onClick={copy} className="ml-auto flex items-center gap-1 rounded px-2 py-1 hover:bg-slate-800 focus-visible:outline focus-visible:outline-emerald-400"><Copy size={13} />复制记录</button>
      <a href="/raw-api.html" target="_blank" rel="noreferrer" className="underline text-slate-300">原始 API 数据</a>
      <span role="status">{copyNote}</span>
    </div>
    <div className="px-4 py-2 text-xs text-slate-400 border-b border-white/10 break-words">{status}</div>
    <div ref={panel} tabIndex={0} aria-label="执行输出记录" onScroll={() => {
      const el = panel.current;
      if (el && el.scrollHeight - el.scrollTop - el.clientHeight > 80) setFollow(false);
    }} className="h-[520px] sm:h-[620px] overflow-y-auto overscroll-contain px-5 py-5 space-y-6">
      {!hasOutput && <p className="text-sm text-slate-400 leading-6">{terminal ? '这次执行未记录输出，请检查生成服务版本。' : '正在连接执行记录…'}</p>}
      {visible.map((log, index) => {
        const text = activityText(log);
        const activity = ['phase_started', 'repair_reserved', 'tool.started', 'tool.completed'].includes(log.kind || '');
        return <article key={log.id != null ? `event-${log.id}` : `legacy-${index}`} className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-xs text-neutral-500 mb-2">
            <Activity size={14} /><span>{activityTitle(log)}</span>
            <time title={log.timestamp}>{log.kind === 'saved.result' ? '已保存题目' : new Date(log.timestamp).toLocaleTimeString('zh-CN', { hour12: false })}</time>
          </div>
          <div className={`whitespace-pre-wrap break-words [overflow-wrap:anywhere] leading-7 ${activity ? 'text-sm text-neutral-400' : log.level === 'error' ? 'text-rose-300 text-sm' : 'text-[15px] text-neutral-200'}`}>
            {text || (terminal ? log.message || '该阶段未返回正文' : '正在接收正文…')}
          </div>
          {(log.data || log.kind) && <details className="mt-2 text-xs text-neutral-500"><summary className="cursor-pointer hover:text-neutral-300">原始返回</summary>
            <pre className="mt-2 whitespace-pre-wrap break-words [overflow-wrap:anywhere] text-neutral-400 leading-5">{JSON.stringify({ run_id: log.run_id, ...(log.data || { message: log.message }) }, null, 2)}</pre>
          </details>}
        </article>;
      })}
      {hasOutput && !visible.length && <p className="text-xs text-slate-400">该角色尚无记录。</p>}
    </div>
    {!follow && <button onClick={() => setFollow(true)} className="w-full py-2 text-xs text-emerald-300 border-t border-white/10 flex justify-center gap-1"><ArrowDown size={14} />回到最新输出</button>}
  </section>;
}
