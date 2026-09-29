import type { JobEventLog } from '../../types/job';
import React from 'react';
import { GenerationJob } from '../../types/job';
import { ConnState } from '../job-progress/jobProgressHelpers';
import { WorkbenchGenerationActivity } from './WorkbenchGenerationActivity';
import { WorkbenchProgressSlots } from './WorkbenchProgressSlots';
import { WorkbenchProgressSummary } from './WorkbenchProgressSummary';

interface Props {
  jobId: string;
  jobStatus: GenerationJob['status']; connState: ConnState; tokensUsed: number | null;
  usageStatus?: string; estimatedCost: number | null; onViewPaper: () => void;
  streamError: string; onRetry: () => void;
  progress: { completed: number; total: number; latestNote: string };
  jobSlots: any[]; activeSlotId: string | null; currentThinking: string;
  recentLogs: JobEventLog[];
}

export const WorkbenchProgressView: React.FC<Props> = props => {
  const percent = Math.min(100, Math.max(0, Math.round((props.progress.completed / Math.max(1, props.progress.total)) * 100)));
  const activeSlot = props.jobSlots.find(slot => slot.slot_id === props.activeSlotId);
  return <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
    <WorkbenchProgressSummary {...props} percent={percent} />
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      <WorkbenchProgressSlots jobId={props.jobId} jobSlots={props.jobSlots} activeSlotId={props.activeSlotId} completed={props.progress.completed} />
      <WorkbenchGenerationActivity {...props} activeSlot={activeSlot} completed={props.progress.completed} />
    </div>
  </div>;
};
