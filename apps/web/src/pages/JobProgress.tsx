import React from 'react';
import { RefreshCw } from 'lucide-react';
import { api } from '../lib/api';
import { TERMINAL_STATUSES, tokensLabelForJob } from './job-progress/jobProgressHelpers';
import { JobProgressDiagnostics } from './job-progress/JobProgressDiagnostics';
import { JobProgressHeader } from './job-progress/JobProgressHeader';
import { JobProgressLogs } from './job-progress/JobProgressLogs';
import { JobProgressMetrics } from './job-progress/JobProgressMetrics';
import { JobProgressSlots } from './job-progress/JobProgressSlots';
import { useJobProgressStream } from './job-progress/useJobProgressStream';

export { QUESTION_KIND_LABELS, questionKindLabel, tokensLabelForJob } from './job-progress/jobProgressHelpers';
interface JobProgressProps { onGoToEditor: () => void; }

export const JobProgress: React.FC<JobProgressProps> = ({ onGoToEditor }) => {
  const stream = useJobProgressStream();
  const { job, connState, connNote, setConnNote, controlBusy, setControlBusy, reconnectAttempt, applyJob } = stream;
  if (!job) return connState === 'reading'
    ? <div className="p-8 text-center text-slate-500">正在读取命题任务状态…</div>
    : <div className="p-8 text-center space-y-3">
      <p className="text-slate-500">当前没有可观察的命题任务，请先确认计划并启动命题。</p>
      {connState === 'disconnected' && <button onClick={stream.handleManualResubscribe} className="px-4 py-2 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 font-semibold text-xs rounded-xl transition flex items-center gap-1.5 mx-auto cursor-pointer"><RefreshCw className="w-3.5 h-3.5" />刷新页面重新读取</button>}
    </div>;

  const isTerminal = TERMINAL_STATUSES.includes(job.status);
  const isCompleted = job.status === 'COMPLETED';
  const usage = tokensLabelForJob({ tokens_used: job.tokens_used, estimated_cost_cny: job.estimated_cost_cny, usage_status: (job as any).usage_status as string | undefined });
  const handlePauseResume = async () => {
    if (controlBusy) return;
    setControlBusy(true);
    try {
      const updated = job.status === 'PAUSED' ? await api.resumeGenerationJob('current') : await api.pauseGenerationJob('current');
      if (updated) applyJob(updated);
      reconnectAttempt.current = 0;
    } catch (error) { setConnNote(String(error)); }
    finally { setControlBusy(false); }
  };
  const handleCancel = async () => {
    if (controlBusy || !window.confirm('确定取消本次出题吗？已产生的候选题会保留，但不会再启动新的模型调用。')) return;
    setControlBusy(true);
    try {
      const updated = await api.cancelGenerationJob('current');
      if (updated) applyJob(updated);
    } catch (error) { setConnNote(String(error)); }
    finally { setControlBusy(false); }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <JobProgressHeader job={job} connState={connState} connNote={connNote} controlBusy={controlBusy}
        onPauseResume={() => { void handlePauseResume(); }} onCancel={() => { void handleCancel(); }}
        onResubscribe={stream.handleManualResubscribe} onGoToEditor={onGoToEditor} />
      <JobProgressMetrics job={job} isTerminal={isTerminal} tokens={usage.tokens} cost={usage.cost} />
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        <JobProgressSlots job={job} />
        <JobProgressLogs job={job} onGoToEditor={onGoToEditor} isCompleted={isCompleted} isTerminal={isTerminal} />
      </div>
      <JobProgressDiagnostics job={job} connState={connState} connNote={connNote} />
    </div>
  );
};

export default JobProgress;
