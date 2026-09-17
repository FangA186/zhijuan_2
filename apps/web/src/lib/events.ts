import { JobEventLog } from '../types/job';

/**
 * SSE 事件流辅助与解析
 */
export interface SseEvent {
  event: 'job_status' | 'slot_update' | 'token_count' | 'log';
  data: JobEventLog | Record<string, any>;
}

export function parseSseMessage(payload: string): SseEvent | null {
  try {
    return JSON.parse(payload) as SseEvent;
  } catch {
    return null;
  }
}
