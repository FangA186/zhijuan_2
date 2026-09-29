import type { ExamBlueprint } from './spec';
import type { JobEventLog } from './job';

export interface PlanningJob {
  job_id: string;
  spec_revision: number;
  request_key: string;
  version: number;
  stale?: boolean;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'RECONCILING' | 'CANCELLED';
  activity: JobEventLog[];
  error?: string;
  result?: ExamBlueprint;
  usage?: Record<string, number>;
}
