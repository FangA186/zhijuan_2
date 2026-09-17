import { BlueprintSlot } from './spec';

export interface GenerationJob {
  job_id: string;
  exam_id: string;
  revision: number;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'CANCELLED' | 'FAILED';
  total_slots: number;
  completed_slots: number;
  tokens_used: number;
  estimated_cost_cny: number;
  started_at: string;
  updated_at: string;
  slots: BlueprintSlot[];
  logs: JobEventLog[];
}

export interface JobEventLog {
  timestamp: string;
  slot_id?: string;
  role: 'planner' | 'author' | 'solver' | 'reviewer' | 'system';
  level: 'info' | 'warn' | 'error';
  message: string;
}
