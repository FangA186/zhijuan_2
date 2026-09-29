import { useEffect, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { GeneratedCandidate } from '../../types/candidate';
import { GenerationJob, JobEventLog } from '../../types/job';
import { api } from '../../lib/api';

import { TERMINAL_STATUSES, type ConnState } from '../job-progress/jobProgressHelpers';
import { applySnapshotSummary } from './jobSnapshotSummary';

interface Args {
  isGenerating: boolean;
  setCandidates: Dispatch<SetStateAction<GeneratedCandidate[]>>;
  setIsGenerating: Dispatch<SetStateAction<boolean>>;
  onCandidatesUpdated?: (candidates: GeneratedCandidate[]) => void;
}

export function useExamPaperStream({ isGenerating, setCandidates, onCandidatesUpdated }: Args) {
  const [jobId, setJobId] = useState('');
  const [jobSlots, setJobSlots] = useState<any[]>([]);
  const [activeSlotId, setActiveSlotId] = useState<string | null>(null);
  const [currentThinking, setCurrentThinking] = useState<string>('等待服务端进度事件...');
  const [tokensUsed, setTokensUsed] = useState<number | null>(null);
  const [usageStatus, setUsageStatus] = useState<string | undefined>(undefined);
  const [estimatedCost, setEstimatedCost] = useState<number | null>(null);
  const [jobStatus, setJobStatus] = useState<GenerationJob['status']>('QUEUED');
  const [streamError, setStreamError] = useState('');
  const [connState, setConnState] = useState<ConnState>('reading');
  const [recentLogs, setRecentLogs] = useState<JobEventLog[]>([]);

  const [generationProgress, setGenerationProgress] = useState({
    completed: 0,
    total: 0,
    latestNote: '正在读取任务状态...',
  });

  const jobStatusRef = useRef<GenerationJob['status']>('QUEUED');

  useEffect(() => {
    if (!isGenerating) return;

    let es: EventSource | null = null;
    let isCancelled = false;
    let disposeRequested = false;

    const applySnapshot = (data: GenerationJob) => {
      applySnapshotSummary(data, { setJobId, setActiveSlotId, setCurrentThinking, setGenerationProgress });
      if (TERMINAL_STATUSES.includes(data.status)) setConnState('disconnected');
      jobStatusRef.current = data.status;
      setJobStatus(data.status);
      setJobSlots(data.slots || []);
      setTokensUsed(data.tokens_used);
      setUsageStatus((data as any).usage_status as string | undefined);
      setEstimatedCost(data.estimated_cost_cny);
      setRecentLogs(data.logs || []);
      if (['FAILED','PARTIAL_FAILED','CANCELLED','RECONCILING'].includes(data.status)) {
        setStreamError(data.status === 'RECONCILING' ? '调用结果尚未核实，已停止继续生成，请先对账。' : data.status === 'CANCELLED' ? '任务已取消，迟到结果不会写入当前试卷。' : '任务未通过生成或检查，失败结果不会冒充已完成。');
        if (es) {
          es.close();
          es = null;
        }
      }
      if (data.status === 'COMPLETED') {
        api.getCandidates().then(fresh => {
          if (disposeRequested) return;
          setCandidates(fresh);
          onCandidatesUpdated?.(fresh);
          if (!fresh.length) setStreamError('任务已完成，但题目尚未可读取');
        }).catch(error => { if (!disposeRequested) setStreamError(String(error)); });
      }
    };

    const getSnapshotAndConnect = () => {
      if (isCancelled || disposeRequested) return;
      setConnState('reading');
      api.getJobActivity().then(data => {
        if (isCancelled || disposeRequested) return;
        if (data) applySnapshot(data);
        if (!data) setStreamError('当前没有命题任务');
        if (data && !TERMINAL_STATUSES.includes(data.status)) openStream();
      }).catch(error => {
        if (isCancelled || disposeRequested) return;
        setStreamError(String(error));
        scheduleReconnect();
      });
    };

    const openStream = () => {
      if (isCancelled || disposeRequested) return;
      setConnState('streaming');
      es = new EventSource(api.getJobActivityStreamUrl());
      es.addEventListener('init', (e: MessageEvent) => {
        if (!isCancelled) applySnapshot(JSON.parse(e.data));
      });

      es.addEventListener('slot_update', (e: MessageEvent) => {
        if (isCancelled) return;
        try {
          const slot = JSON.parse(e.data);
          setActiveSlotId(slot.slot_id);
          setJobSlots((prev) => {
            const idx = prev.findIndex((s) => s.slot_id === slot.slot_id);
            if (idx !== -1) {
              const next = [...prev];
              next[idx] = { ...next[idx], ...slot };
              return next;
            }
            return [...prev, slot];
          });

          if (slot.status === 'READY' || slot.status === 'REVIEW_REQUIRED') {
            setGenerationProgress((prev) => ({
              ...prev,
              latestNote: `第 ${slot.order} 题【${slot.target_topic}】状态：${slot.status === 'REVIEW_REQUIRED' ? '待教师复核' : '已就绪'}`,
            }));
          }
        } catch {}
      });

      es.addEventListener('log', (e: MessageEvent) => {
        if (isCancelled) return;
        try {
          const item = JSON.parse(e.data);
          if (item.message) {
            setGenerationProgress((prev) => ({
              ...prev,
              latestNote: item.message,
            }));
            setCurrentThinking(item.message);
            setRecentLogs((prev) => [...prev, item]);
          }
        } catch {}
      });

      es.addEventListener('job_metrics', (e: MessageEvent) => {
        if (isCancelled) return;
        try {
          const m = JSON.parse(e.data);
          setTokensUsed(m.tokens_used ?? null);
          setUsageStatus((m as any).usage_status as string | undefined);
          setEstimatedCost(m.estimated_cost_cny ?? null);
          if (typeof m.completed_slots === 'number') {
            setGenerationProgress(prev => ({ ...prev, completed: m.completed_slots }));
          }
        } catch {}
      });

      es.addEventListener('completed', (event: MessageEvent) => {
        if (!isCancelled) applySnapshot(JSON.parse(event.data));
        if (es) es.close();
        es = null;
      });

      es.addEventListener('failed', (event: MessageEvent) => {
        if (!isCancelled) applySnapshot(JSON.parse(event.data));
      });
      es.addEventListener('cancelled', (event: MessageEvent) => {
        if (!isCancelled) applySnapshot(JSON.parse(event.data));
      });
      es.addEventListener('error', (e: Event) => {
        if (isCancelled) return;
        const msgData = (e as MessageEvent).data;
        if (typeof msgData === 'string' && msgData.length > 0) {
          if (es) es.close();
          es = null;
          setConnState('disconnected');
          setStreamError('服务端未返回可订阅的任务流，请刷新页面读取任务状态');
          return;
        }
        scheduleReconnect();
      });
    };

    const scheduleReconnect = () => {
      if (isCancelled || disposeRequested) return;
      if (TERMINAL_STATUSES.includes(jobStatusRef.current)) {
        setConnState('disconnected');
        setStreamError('任务已结束，实时订阅已停止。可按“查看已生成题目”或“重新读取任务状态”操作。');
        return;
      }
      setConnState('reconnecting');
      setStreamError('进度连接中断，正在重新读取任务状态…（不会重复启动出题）');
      window.setTimeout(() => {
        if (isCancelled || disposeRequested) return;
        getSnapshotAndConnect();
      }, 2000);
    };

    getSnapshotAndConnect();

    return () => {
      isCancelled = true;
      disposeRequested = true;
      if (es) { es.close(); es = null; }
    };
  }, [isGenerating]);
  return { jobId, jobSlots, setJobSlots, activeSlotId, setActiveSlotId, currentThinking,
    tokensUsed, usageStatus, estimatedCost, jobStatus, streamError,
    setStreamError, connState, recentLogs, generationProgress };
}
