import { topicLabel } from '../../lib/topicPlanning';
import React from 'react';
import { useSlotDiagnostics } from './useSlotDiagnostics';
import { Activity, AlertTriangle, Check, Cpu, Sparkles } from 'lucide-react';
import { formatScoreX100 } from '../../lib/scoring';
import { questionKindLabel } from '../job-progress/jobProgressHelpers';

interface Props { jobId: string; jobSlots: any[]; activeSlotId: string | null; completed: number; }
export const WorkbenchProgressSlots: React.FC<Props> = ({ jobId, jobSlots, activeSlotId, completed }) => {
  const reasons = useSlotDiagnostics(jobId, completed);
  return (
  <div className="lg:col-span-5 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3 max-h-[580px] flex flex-col">
    <div className="flex items-center justify-between border-b border-slate-100 pb-3">
      <span className="font-bold text-sm text-slate-800 flex items-center gap-2"><Cpu className="w-4 h-4 text-brand-600" />试卷考点题槽清单 ({jobSlots.length} 题)</span>
      <span className="text-[11px] text-slate-400">实时状态机驱动</span>
    </div>
    <div className="overflow-y-auto pr-1 space-y-2 flex-1 divide-y divide-slate-50">
      {jobSlots.map(slot => {
        const isActive = ['AUTHORING', 'SOLVING'].includes(slot.status) && slot.slot_id === activeSlotId;
        const isReview = slot.status === 'REVIEW_REQUIRED';
        const isReady = slot.status === 'READY' || isReview;
        const isSolving = slot.status === 'SOLVING';
        const isAuthoring = slot.status === 'AUTHORING';
        return <div key={slot.slot_id} className={`pt-2 p-2.5 rounded-xl transition-all text-xs ${isActive ? 'bg-brand-50/80 border border-brand-300 ring-1 ring-brand-300/50' : isReady ? 'bg-slate-50/70 border border-slate-200/80' : 'hover:bg-slate-50/50 border border-transparent'}`}>
          <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="font-mono font-bold text-slate-500 shrink-0 w-6">{String(slot.order).padStart(2, '0')}</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-200/80 text-[10px] font-semibold text-slate-700 shrink-0">{questionKindLabel(slot.kind)}</span>
            <span className="truncate text-slate-800 font-medium" title={topicLabel(slot.target_topic)}>{topicLabel(slot.target_topic)}</span>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[10px] font-mono text-slate-400">{formatScoreX100(slot.score_x100 || 500)}分</span>
            {slot.status === 'FAIL' ? <span className="rounded bg-rose-100 px-2 py-1 font-bold text-rose-800">失败</span> : isReview ? <span className="px-2 py-0.5 rounded-md bg-amber-100 text-amber-800 font-bold text-[10px] flex items-center gap-1"><AlertTriangle className="w-3 h-3 text-amber-600" />待教师复核</span>
              : isReady ? <span className="px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 font-bold text-[10px] flex items-center gap-1"><Check className="w-3 h-3 text-emerald-600" />已就绪</span>
              : isSolving ? <span className="px-2 py-0.5 rounded-md bg-purple-100 text-purple-800 font-bold text-[10px] flex items-center gap-1 animate-pulse"><Activity className="w-3 h-3 text-purple-600 animate-spin" />做题验算中</span>
              : isAuthoring ? <span className="px-2 py-0.5 rounded-md bg-blue-100 text-blue-800 font-bold text-[10px] flex items-center gap-1"><Sparkles className="w-3 h-3 text-blue-600 animate-pulse" />命题构思中</span>
              : <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-500 font-medium text-[10px]">待出题</span>}
          </div>
          </div>
          {['FAIL', 'REVIEW_REQUIRED'].includes(slot.status) && <ul aria-label={`第${slot.order}题原因`} className="mt-2 space-y-1 break-words text-slate-600">
            {reasons(slot).map((reason, index) => <li key={index}>· {reason}</li>)}
          </ul>}
        </div>;
      })}
    </div>
  </div>
);
};
