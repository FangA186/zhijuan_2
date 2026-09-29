import { BlueprintSlot } from './spec';

export interface GenerationJob {
  job_id: string;
  exam_id: string;
  revision: number;
  status: 'QUEUED' | 'RUNNING' | 'PAUSED' | 'RECONCILING' | 'COMPLETED' | 'PARTIAL_FAILED' | 'CANCELLED' | 'FAILED';
  total_slots: number;
  completed_slots: number;
  tokens_used: number | null;
  estimated_cost_cny: number | null;
  started_at: string;
  updated_at: string;
  slots: BlueprintSlot[];
  logs: JobEventLog[];
}

export interface JobEventLog {
  id?: number | string;
  kind?: string;
  attempt?: number;
  run_id?: string;
  data?: Record<string, unknown>;
  timestamp: string;
  slot_id?: string;
  role: 'planner' | 'author' | 'solver' | 'reviewer' | 'system' | 'think';
  level: 'info' | 'warn' | 'error';
  message: string;
}

/** C6: 前端运行状态 – 来自 /v1/readyz 规范化的运行时就绪快照 */
export interface GenerationRuntimeState {
  ready: boolean | null;
  configured: boolean | null;
  reasonCodes: string[];
  components: Record<string, { ok: boolean | null }>;
  checkedAt: string | null;
  versionConfirmed: boolean;
}
