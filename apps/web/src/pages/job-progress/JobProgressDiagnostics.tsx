import React from 'react';
import { GenerationJob } from '../../types/job';
import { ConnState } from './jobProgressHelpers';

export const JobProgressDiagnostics: React.FC<{ job: GenerationJob; connState: ConnState; connNote: string }> = ({ job, connState, connNote }) => (
  <details className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-xs text-slate-500">
    <summary className="cursor-pointer font-semibold text-slate-600">开发信息（诊断用）</summary>
    <div className="mt-2 space-y-1">
      <div>任务状态：{job.status}</div><div>任务 ID：{job.job_id}</div><div>规格版本 revision：{job.revision}</div>
      <div>连接状态：{connState}{connNote ? ` · ${connNote}` : ''}</div>
      <div>usage_status：{((job as any).usage_status as string | undefined) ?? 'UNKNOWN'}</div>
    </div>
  </details>
);
