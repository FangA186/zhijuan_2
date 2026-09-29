import { useEffect, useRef, useState } from 'react';
import { api } from '../../lib/api';
import type { PlanningJob } from '../../types/planning';
import type { ExamSpec } from '../../types/spec';
import type { LoadedFoolproofSetupState } from './useFoolproofSetupBase';

export function usePlanner(state: LoadedFoolproofSetupState) {
  const [planning, setPlanning] = useState<PlanningJob | null>(null);
  const [planningError, setPlanningError] = useState('');
  const latest = useRef(state); latest.current = state;
  const fingerprint = useRef(JSON.stringify(state.spec));
  const pendingKey = useRef<string | null>(null);
  const [connecting, setConnecting] = useState(true);
  const alive = useRef(true);
  const receive = (job: PlanningJob | null) => {
    if (!alive.current) return;
    setPlanning(job);
    if (!job?.stale && job?.status === 'COMPLETED' && job.result && fingerprint.current === JSON.stringify(latest.current.spec)) {
      latest.current.setPreview(job.result);
      latest.current.setPreviewSpec(fingerprint.current);
    }
  };
  useEffect(() => {
    alive.current = true;
    let timer: ReturnType<typeof setTimeout>;
    const read = async () => {
      try { receive(await api.getPlanning()); setPlanningError(''); setConnecting(false); }
      catch { if (alive.current) { setPlanningError('读取规划记录失败；重连只读取状态，不会重复调用模型。'); setConnecting(true); } }
      if (alive.current) timer = setTimeout(read, 1500);
    };
    void read();
    return () => { alive.current = false; clearTimeout(timer); };
  }, []);
  const beginPlanning = async (saved: ExamSpec) => {
    fingerprint.current = JSON.stringify(saved);
    pendingKey.current ??= crypto.randomUUID();
    setConnecting(true);
    try {
      const job = await api.startPlanning(pendingKey.current);
      receive(job); pendingKey.current = null; setPlanningError('');
    } catch (error) {
      setPlanningError(`${error instanceof Error ? error.message : '规划启动结果未知'}；请读取任务状态后再操作。`);
      // Preserve this key across manual retries after a lost response.
      throw error;
    } finally { setConnecting(false); }
  };
  const cancelPlanning = async () => {
    if (planning) {
      try { receive(await api.cancelPlanning(planning.job_id)); }
      catch (error) { setPlanningError(error instanceof Error ? error.message : '取消失败'); }
    }
  };
  const planningBusy = connecting || planning?.status === 'QUEUED' || planning?.status === 'RUNNING' || planning?.status === 'RECONCILING';
  return { planning, planningError, planningBusy, beginPlanning, cancelPlanning };
}
