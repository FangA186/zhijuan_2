import React from 'react';
import { CheckCircle2, ShieldCheck, Sparkles } from 'lucide-react';
import { GenerationJob, JobEventLog } from '../../types/job';
import { ConnState, TERMINAL_STATUSES } from '../job-progress/jobProgressHelpers';
import { AgentActivityConsole } from '../job-progress/AgentActivityConsole';

interface Props {
  jobStatus: GenerationJob['status']; connState: ConnState; activeSlot: any;
  completed: number; jobSlots: any[]; currentThinking: string;
  recentLogs: JobEventLog[];
  tokensUsed: number | null; usageStatus?: string;
}

export const WorkbenchGenerationActivity: React.FC<Props> = props => {
  return (
    <div className="lg:col-span-7 space-y-4">
      <AgentActivityConsole logs={props.recentLogs} terminal={TERMINAL_STATUSES.includes(props.jobStatus)} status={props.currentThinking} />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
        <Note icon={<Sparkles className="w-3.5 h-3.5 text-blue-600" />} title="1. 命题骨干原创">基于课标和考点原创构造真实 LaTeX 题干与高辨识度选项。</Note>
        <Note icon={<ShieldCheck className="w-3.5 h-3.5 text-purple-600" />} title="2. 盲解独立求证">不给答案背靠背独立解题，验算解的存在性、唯一性与自洽性。</Note>
        <Note icon={<CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />} title="3. 审核与有限修订">审查题目与检查结果，最多修订两轮；修改后重新检查与盲解。</Note>
      </div>
      <details className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-xs text-slate-500">
        <summary className="cursor-pointer font-semibold text-slate-600">开发信息（诊断用）</summary>
        <div className="mt-2 space-y-1"><div>任务状态：{props.jobStatus}</div><div>题槽状态：{props.jobSlots.map(slot => `${slot.slot_id}:${slot.status}`).join('，') || '（空）'}</div>
          <div>连接状态：{props.connState}</div><div>token 字段：{props.tokensUsed == null ? 'null（未知）' : props.tokensUsed}{props.usageStatus ? ` · usage_status=${props.usageStatus}` : ''}</div>
        </div>
      </details>
    </div>
  );
};

const Note: React.FC<{ icon: React.ReactNode; title: string; children: React.ReactNode }> = ({ icon, title, children }) => (
  <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-1">
    <div className="font-bold text-slate-800 flex items-center gap-1 text-[11px]">{icon}{title}</div>
    <div className="text-[11px] text-slate-500">{children}</div>
  </div>
);
