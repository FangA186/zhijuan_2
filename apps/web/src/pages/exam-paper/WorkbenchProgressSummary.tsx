import React from 'react';
import { ArrowRight, Brain, RefreshCw } from 'lucide-react';
import { GenerationJob } from '../../types/job';
import { ConnState, JOB_STATUS_LABELS, TERMINAL_STATUSES } from '../job-progress/jobProgressHelpers';

interface Props {
  jobStatus: GenerationJob['status']; connState: ConnState; tokensUsed: number | null;
  usageStatus?: string; estimatedCost: number | null; onViewPaper: () => void;
  streamError: string; onRetry: () => void;
  progress: { completed: number; total: number; latestNote: string }; percent: number;
}

export const WorkbenchProgressSummary: React.FC<Props> = props => (
  <>
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
      <div className="flex items-center gap-3.5">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-500 to-indigo-600 text-white flex items-center justify-center shadow-md shadow-brand-500/20">
          <Brain className={`w-6 h-6 ${TERMINAL_STATUSES.includes(props.jobStatus) ? '' : 'animate-pulse'}`} />
        </div>
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2"><span>命题任务进度</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-brand-50 text-brand-700 border border-brand-200 font-semibold">{JOB_STATUS_LABELS[props.jobStatus] ?? '任务处理中'}</span>
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">依据服务端任务状态展示题槽进度</p>
        </div>
      </div>
      <div className="flex items-center gap-4 text-xs">
        <div className={`px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-600 ${props.connState === 'disconnected' ? 'border-rose-200 text-rose-600' : props.connState === 'reconnecting' ? 'border-amber-200 text-amber-600' : ''}`}>
          <span className="text-slate-400">{props.connState === 'reconnecting' ? '连接重连中: ' : props.connState === 'disconnected' && !TERMINAL_STATUSES.includes(props.jobStatus) ? '连接中断: ' : 'Tokens 消耗: '}</span>
          <span className={`font-bold font-mono ${props.connState === 'disconnected' ? 'text-rose-600' : 'text-slate-800'}`}>
            {props.usageStatus === 'PARTIAL_UNKNOWN' ? '部分已知（总量未知）' : props.tokensUsed == null ? '未知' : props.tokensUsed.toLocaleString()}
          </span>
        </div>
        <div className="px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-600"><span className="text-slate-400">成本预估: </span>
          <span className="font-bold text-emerald-600 font-mono">{props.estimatedCost == null ? '未知' : `¥${props.estimatedCost.toFixed(3)}`}</span>
        </div>
        <button type="button" onClick={props.onViewPaper} disabled={props.jobStatus !== 'COMPLETED' && props.jobStatus !== 'PARTIAL_FAILED'}
          className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs rounded-xl shadow-xs transition flex items-center gap-1.5 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed">
          <span>{props.jobStatus === 'PARTIAL_FAILED' ? '查看已生成的题目' : '提前查看已生成题目'}</span><ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
    {props.streamError && <div role="alert" className={`rounded-lg p-3 text-sm font-medium ${props.jobStatus === 'RECONCILING' ? 'bg-amber-50 text-amber-800' : TERMINAL_STATUSES.includes(props.jobStatus) && props.jobStatus !== 'COMPLETED' ? 'bg-rose-50 text-rose-800' : props.connState === 'reconnecting' ? 'bg-amber-50 text-amber-800' : 'bg-rose-50 text-rose-800'}`}>
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"><span>{props.streamError}</span>
        {props.connState === 'disconnected' && <button type="button" onClick={props.onRetry} className="px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 font-semibold text-xs rounded-xl transition flex items-center gap-1.5 shrink-0 cursor-pointer"><RefreshCw className="w-3.5 h-3.5" />重新读取任务状态</button>}
        {TERMINAL_STATUSES.includes(props.jobStatus) && props.jobStatus !== 'COMPLETED' && <span className="min-w-0 text-[11px] opacity-80">已停止自动重连，不会重复发起出题</span>}
      </div>
    </div>}
    <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
      <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
        <span className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-brand-500 animate-ping" /><span>流水线推进进度</span></span>
        <span className="text-brand-600 font-bold font-mono">{props.progress.completed} / {props.progress.total} 题 ({props.percent}%)</span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden"><div className="bg-gradient-to-r from-brand-500 to-indigo-600 h-full rounded-full transition-all duration-300 ease-out" style={{ width: `${props.percent}%` }} /></div>
      <div className="text-[11px] text-slate-500 truncate">{props.progress.latestNote}</div>
    </div>
  </>
);
