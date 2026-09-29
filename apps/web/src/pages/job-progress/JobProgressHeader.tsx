import React from 'react';
import { ArrowRight, Pause, Play, RefreshCw, XCircle } from 'lucide-react';
import { GenerationJob } from '../../types/job';
import { ConnState, JOB_STATUS_LABELS, terminalNotice } from './jobProgressHelpers';

interface Props {
  job: GenerationJob;
  connState: ConnState;
  connNote: string;
  controlBusy: boolean;
  onPauseResume: () => void;
  onCancel: () => void;
  onResubscribe: () => void;
  onGoToEditor: () => void;
}

export const JobProgressHeader: React.FC<Props> = props => {
  const { job, connState } = props;
  const terminal = terminalNotice(job.status);
  const paused = job.status === 'PAUSED';
  const completed = job.status === 'COMPLETED';
  const isTerminal = ['FAILED', 'PARTIAL_FAILED', 'CANCELLED', 'RECONCILING', 'COMPLETED'].includes(job.status);
  const showControls = ['QUEUED', 'RUNNING', 'PAUSED', 'RECONCILING'].includes(job.status);
  return (
    <>
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-brand-100 text-brand-800">阶段二 · AI 智能出题</span>
            <h1 className="text-xl font-bold text-slate-900">{isTerminal ? JOB_STATUS_LABELS[job.status] : 'AI 智能原创出题与双重验算中'}</h1>
          </div>
          <p className="text-sm text-slate-500">严格对齐新课标教学大纲，AI 命题名师构思题干，独立做题教师双重验算解法，智能大纲考点把关。</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-full border ${connState === 'disconnected' ? 'bg-rose-50 text-rose-700 border-rose-200' : connState === 'reconnecting' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'}`}>
            <RefreshCw className={`w-3.5 h-3.5 ${connState !== 'disconnected' ? 'animate-spin' : ''}`} />
            {connState === 'disconnected' ? '连接中断' : connState === 'reconnecting' ? '重连读取中' : connState === 'reading' ? '读取中' : '实时更新中'}
          </span>
          {showControls && <>
            <button onClick={props.onPauseResume} disabled={props.controlBusy} className="px-3.5 py-2 border border-slate-300 hover:bg-slate-100 text-slate-700 font-semibold text-xs rounded-xl flex items-center gap-1.5 transition disabled:opacity-50 cursor-pointer">
              {paused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}<span>{paused ? '继续出题' : '暂停出题'}</span>
            </button>
            <button onClick={props.onCancel} disabled={props.controlBusy} className="px-3.5 py-2 border border-rose-200 hover:bg-rose-50 text-rose-700 font-semibold text-xs rounded-xl flex items-center gap-1.5 transition disabled:opacity-50 cursor-pointer">
              <XCircle className="w-3.5 h-3.5" /><span>取消出题</span>
            </button>
          </>}
          {(completed || job.status === 'PARTIAL_FAILED') && <button onClick={props.onGoToEditor} className="px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-sm rounded-xl flex items-center gap-2 shadow-sm transition">进入试卷排版与修改<ArrowRight className="w-4 h-4" /></button>}
        </div>
      </div>
      {props.connNote && <div role="status" className="rounded-lg bg-slate-50 p-3 text-slate-700 text-xs border border-slate-200">
        <div className="flex items-center justify-between gap-3"><span>{props.connNote}</span>
          {connState === 'disconnected' && <button onClick={props.onResubscribe} className="px-3 py-1.5 bg-white hover:bg-slate-100 border border-slate-300 text-slate-700 font-semibold text-xs rounded-xl transition flex items-center gap-1.5 shrink-0 cursor-pointer"><RefreshCw className="w-3.5 h-3.5" />重新读取任务状态</button>}
        </div>
      </div>}
      {terminal && <div role="status" className={`rounded-lg p-3 text-sm font-medium ${terminal.tone}`}>{terminal.text}</div>}
    </>
  );
};
