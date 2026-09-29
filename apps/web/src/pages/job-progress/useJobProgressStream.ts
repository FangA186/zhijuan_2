import { useCallback, useEffect, useRef, useState } from 'react';
import { BlueprintSlot } from '../../types/spec';
import { GenerationJob, JobEventLog } from '../../types/job';
import { api } from '../../lib/api';
import { ConnState, JOB_STATUS_LABELS, TERMINAL_STATUSES } from './jobProgressHelpers';

export function useJobProgressStream() {
  const [job, setJob] = useState<GenerationJob | null>(null);
  const [connState, setConnState] = useState<ConnState>('reading');
  const [connNote, setConnNote] = useState('');
  const [controlBusy, setControlBusy] = useState(false);
  const reconnectAttempt = useRef(0);
  const jobStatusRef = useRef<GenerationJob['status'] | null>(null);
  const manualReconnectRef = useRef<(() => void) | null>(null);

  const applyJob = useCallback((data: GenerationJob) => {
    jobStatusRef.current = data.status;
    setJob(data);
  }, []);

  // 连接后端实时流式推送；掉线时先 GET 对账，再重新订阅，绝不把“再次 POST 启动”当重连动作
  useEffect(() => {
    let es: EventSource | null = null;
    let isCancelled = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    const maxRetries = 8;

    const closeStream = () => {
      if (es) {
        es.close();
        es = null;
      }
    };

    const openStream = () => {
      if (isCancelled) return;
      setConnState('streaming');
      setConnNote('');
      es = new EventSource(api.getJobActivityStreamUrl());

      es.addEventListener('init', (e: MessageEvent) => {
        if (isCancelled) return;
        try {
          applyJob(JSON.parse(e.data) as GenerationJob);
        } catch {}
      });

      es.addEventListener('slot_update', (e: MessageEvent) => {
        if (isCancelled) return;
        try {
          const slot: BlueprintSlot = JSON.parse(e.data);
          setJob((prev) => {
            if (!prev) return prev;
            const updated = prev.slots.map((s) => (s.slot_id === slot.slot_id ? { ...s, ...slot } : s));
            jobStatusRef.current = prev.status;
            return { ...prev, slots: updated, updated_at: new Date().toISOString() };
          });
        } catch {}
      });

      es.addEventListener('log', (e: MessageEvent) => {
        if (isCancelled) return;
        try {
          const logItem: JobEventLog = JSON.parse(e.data);
          setJob((prev) => {
            if (!prev) return prev;
            jobStatusRef.current = prev.status;
            return { ...prev, logs: [...prev.logs, logItem], updated_at: new Date().toISOString() };
          });
        } catch {}
      });

      es.addEventListener('job_metrics', (e: MessageEvent) => {
        if (isCancelled) return;
        try {
          const m = JSON.parse(e.data);
          setJob((prev) => {
            if (!prev) return prev;
            jobStatusRef.current = prev.status;
            return {
              ...prev,
              tokens_used: typeof m.tokens_used === 'number' ? m.tokens_used : prev.tokens_used,
              estimated_cost_cny: typeof m.estimated_cost_cny === 'number' ? m.estimated_cost_cny : prev.estimated_cost_cny,
              completed_slots: typeof m.completed_slots === 'number' ? m.completed_slots : prev.completed_slots,
            };
          });
        } catch {}
      });

      const finishTerminal = (data: GenerationJob) => {
        if (isCancelled) return;
        applyJob(data);
        closeStream();
      };

      es.addEventListener('completed', (e: MessageEvent) => {
        if (isCancelled) return;
        try { finishTerminal(JSON.parse(e.data) as GenerationJob); } catch {}
      });
      es.addEventListener('failed', (e: MessageEvent) => {
        if (isCancelled) return;
        try { finishTerminal(JSON.parse(e.data) as GenerationJob); } catch {}
      });
      es.addEventListener('cancelled', (e: MessageEvent) => {
        if (isCancelled) return;
        try { finishTerminal(JSON.parse(e.data) as GenerationJob); } catch {}
      });

      es.addEventListener('error', (e: Event) => {
        // EventSource 的 'error' 事件同时覆盖两种情形：
        // 1) 服务端发送 event: error（带 data）→ 流已终止，停止自动重连；
        // 2) 传输断开（data 为空）→ 按掉线处理，先 GET 对账再重新订阅。
        if (isCancelled) return;
        const msgData = (e as MessageEvent).data;
        if (typeof msgData === 'string' && msgData.length > 0) {
          closeStream();
          setConnState('disconnected');
          setConnNote('服务端未返回可订阅的任务流，已停止自动重连。请先返回配置页确认计划，或刷新页面重新读取。');
          return;
        }
        closeStream();
        scheduleReconnect();
      });
    };

    const reconcileAndSubscribe = async () => {
      // 先 GET 对账：恢复顺序=先读取当前任务快照，再重新订阅
      setConnState('reading');
      setConnNote('');
      try {
        const fresh = await api.getJobActivity();
        if (isCancelled) return;
        if (fresh) {
          applyJob(fresh);
        } else {
          setJob(null);
        }
        openStream();
      } catch (err) {
        console.warn('读取任务失败，稍后重试:', err);
        scheduleReconnect();
      }
    };

    const scheduleReconnect = () => {
      if (isCancelled) return;
      // 终态（含 COMPLETED）不重连：服务端流结束后的 EOF 不应触发无限重连
      const cur = jobStatusRef.current;
      if (cur && TERMINAL_STATUSES.includes(cur)) {
        setConnState('disconnected');
        setConnNote(`任务已处于 ${JOB_STATUS_LABELS[cur] ?? cur}，实时订阅已结束。`);
        return;
      }
      if (reconnectAttempt.current >= maxRetries) {
        setConnState('disconnected');
        setConnNote('与服务器连接中断且重连失败，请点击“重新读取任务状态”手动恢复（不会重复发起出题）。');
        return;
      }
      setConnState('reconnecting');
      setConnNote('进度连接中断，正在重新读取任务状态并恢复订阅…');
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempt.current), 15000);
      reconnectAttempt.current += 1;
      retryTimer = setTimeout(() => {
        if (isCancelled) return;
        reconcileAndSubscribe();
      }, delay);
    };

    const handleManualReconnect = () => {
      if (retryTimer) {
        clearTimeout(retryTimer);
        retryTimer = null;
      }
      reconnectAttempt.current = 0;
      reconcileAndSubscribe();
    };
    manualReconnectRef.current = handleManualReconnect;

    // 初始进入：先 GET 读取当前任务，再订阅流
    reconcileAndSubscribe();

    return () => {
      isCancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      closeStream();
      manualReconnectRef.current = null;
    };
  }, [applyJob]);

  // 手动恢复订阅：只 GET 对账后重新订阅，不发起任何启动 POST
  const handleManualResubscribe = () => {
    manualReconnectRef.current?.();
  };
  return { job, setJob, connState, setConnState, connNote, setConnNote, controlBusy, setControlBusy,
    reconnectAttempt, jobStatusRef, manualReconnectRef, applyJob, handleManualResubscribe };
}
