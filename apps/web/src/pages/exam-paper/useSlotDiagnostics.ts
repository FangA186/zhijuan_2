import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { slotReasons, type DiagnosticSlot, type SlotValidation } from './slotDiagnostics';

export function useSlotDiagnostics(jobId: string, completed: number) {
  const [data, setData] = useState<{ jobId: string; records: Record<string, SlotValidation>; candidates: any[] } | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    setError('');
    Promise.all([api.getValidationRecords(), api.getCandidates()]).then(([records, candidates]) => {
      if (!cancelled) setData({ jobId, records: records as unknown as Record<string, SlotValidation>, candidates });
    }).catch(() => { if (!cancelled) setError('逐题检查记录读取失败，请刷新页面重试。'); });
    return () => { cancelled = true; };
  }, [jobId, completed]);
  return (slot: DiagnosticSlot) => error ? [error]
    : data?.jobId === jobId ? slotReasons(slot, jobId, data.records, data.candidates) : ['正在读取本题检查记录…'];
}
