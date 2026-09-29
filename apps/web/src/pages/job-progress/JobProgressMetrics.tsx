import React from 'react';
import { Activity, CheckCircle2, Sparkles, Target } from 'lucide-react';
import { GenerationJob } from '../../types/job';
import { StatusBadge } from '../../components/StatusBadge';

interface Props { job: GenerationJob; isTerminal: boolean; tokens: string; cost: string; }
export const JobProgressMetrics: React.FC<Props> = ({ job, isTerminal, tokens, cost }) => (
  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
    <Metric icon={<CheckCircle2 className="w-6 h-6" />} color="emerald" title="出题完成进度">
      <div className="text-xl font-bold text-slate-900 mt-0.5">{job.completed_slots} / {job.total_slots} 题</div><div className="text-[11px] text-slate-400">严格按大纲知识点依次生成</div>
    </Metric>
    <Metric icon={<Sparkles className="w-6 h-6" />} color="indigo" title="Token 用量（受信计量）">
      <div className="text-xl font-bold text-slate-900 mt-0.5">{tokens}</div><div className="text-[11px] text-slate-400">费用预估：{cost}</div>
    </Metric>
    <Metric icon={<Target className="w-6 h-6" />} color="blue" title="大纲考点覆盖率">
      <div className="text-xl font-bold text-slate-900 mt-0.5">待检查</div><div className="text-[11px] text-slate-400">题型与认知层次精准对齐</div>
    </Metric>
    <Metric icon={<Activity className="w-6 h-6" />} color="purple" title="当前出题状态">
      <div className="text-sm font-bold text-slate-900 mt-1 flex items-center gap-1.5"><StatusBadge status={job.status} showIcon size="sm" /></div>
      <div className="text-[11px] text-slate-400 mt-0.5">{isTerminal ? '本任务已结束' : '双角色严格隔离做题验算'}</div>
    </Metric>
  </div>
);

const TONES: Record<string, string> = {
  emerald: 'bg-emerald-50 text-emerald-600', indigo: 'bg-indigo-50 text-indigo-600',
  blue: 'bg-blue-50 text-blue-600', purple: 'bg-purple-50 text-purple-600',
};
const Metric: React.FC<{ icon: React.ReactNode; color: string; title: string; children: React.ReactNode }> = ({ icon, color, title, children }) => (
  <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex items-center gap-4">
    <div className={`w-12 h-12 rounded-xl ${TONES[color]} flex items-center justify-center`}>{icon}</div>
    <div><div className="text-xs text-slate-500 font-medium">{title}</div>{children}</div>
  </div>
);
