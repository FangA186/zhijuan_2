import React, { useState, useEffect } from 'react';
import { Play, Pause, XCircle, ArrowRight, Activity, Zap, Coins, CheckCircle2, ShieldAlert } from 'lucide-react';
import { BlueprintSlot } from '../types/spec';
import { GenerationJob, JobEventLog } from '../types/job';
import { api } from '../lib/api';
import { StatusBadge } from '../components/StatusBadge';
import { formatScoreX100 } from '../lib/scoring';

interface JobProgressProps {
  onGoToEditor: () => void;
}

export const JobProgress: React.FC<JobProgressProps> = ({ onGoToEditor }) => {
  const [job, setJob] = useState<GenerationJob | null>(null);
  const [isPaused, setIsPaused] = useState(false);

  useEffect(() => {
    initJob();
  }, []);

  const initJob = async () => {
    const j = await api.startGenerationJob('exam_demo_01');
    setJob(j);
  };

  // 模拟异步任务状态推进流
  useEffect(() => {
    if (!job || job.status === 'COMPLETED' || job.status === 'CANCELLED' || isPaused) return;

    const timer = setInterval(() => {
      setJob((prev) => {
        if (!prev) return null;

        // 找第一个不是 READY/REVIEW_REQUIRED 的 slot
        const updatedSlots = [...prev.slots];
        const nextPendingIdx = updatedSlots.findIndex(
          (s) => s.status !== 'READY' && s.status !== 'REVIEW_REQUIRED'
        );

        const newLogs = [...prev.logs];

        if (nextPendingIdx === -1) {
          // 全部完成
          return {
            ...prev,
            status: 'COMPLETED',
            completed_slots: prev.total_slots,
            logs: [
              ...newLogs,
              {
                timestamp: new Date().toISOString(),
                role: 'system',
                level: 'info',
                message: '所有题目槽位生成、盲解与多维校验已完成！就绪进入编辑工作台。',
              },
            ],
          };
        }

        const currentSlot = updatedSlots[nextPendingIdx];
        let nextStatus: BlueprintSlot['status'] = 'AUTHORING';
        let logMsg = '';
        let role: JobEventLog['role'] = 'author';

        if (currentSlot.status === 'PENDING') {
          nextStatus = 'AUTHORING';
          logMsg = `[#${currentSlot.order} ${currentSlot.target_topic}] Hermes 调用 DeepSeek 原创命题生成中...`;
          role = 'author';
        } else if (currentSlot.status === 'AUTHORING') {
          nextStatus = 'SOLVING';
          logMsg = `[#${currentSlot.order}] 题面已生成，启动独立隔离盲解 (blind-solver)，严格隔离参考答案...`;
          role = 'solver';
        } else if (currentSlot.status === 'SOLVING') {
          nextStatus = 'CHECKING';
          logMsg = `[#${currentSlot.order}] 盲解一致性验证完成，执行 SymPy 数学代数与大纲边界检查...`;
          role = 'reviewer';
        } else if (currentSlot.status === 'CHECKING') {
          // 80% 几率 READY，20% REVIEW_REQUIRED
          const isReview = currentSlot.order === 3 || currentSlot.order === 11;
          nextStatus = isReview ? 'REVIEW_REQUIRED' : 'READY';
          logMsg = isReview
            ? `[#${currentSlot.order}] 规则校验提示教学范围需确认，标记 [REVIEW_REQUIRED] 待教师人工核对。`
            : `[#${currentSlot.order}] 全部可信规则校验通过，标记 [READY]！`;
          role = 'reviewer';
        }

        updatedSlots[nextPendingIdx] = { ...currentSlot, status: nextStatus };

        const completedCount = updatedSlots.filter(
          (s) => s.status === 'READY' || s.status === 'REVIEW_REQUIRED'
        ).length;

        newLogs.push({
          timestamp: new Date().toLocaleTimeString(),
          slot_id: currentSlot.slot_id,
          role,
          level: 'info',
          message: logMsg,
        });

        // 截断日志保持最近 30 条
        if (newLogs.length > 30) newLogs.shift();

        return {
          ...prev,
          slots: updatedSlots,
          completed_slots: completedCount,
          tokens_used: prev.tokens_used + Math.floor(Math.random() * 800 + 400),
          estimated_cost_cny: Number((prev.estimated_cost_cny + 0.015).toFixed(3)),
          logs: newLogs,
          updated_at: new Date().toISOString(),
        };
      });
    }, 1100);

    return () => clearInterval(timer);
  }, [job, isPaused]);

  if (!job) return <div className="p-8 text-center text-slate-500">正在初始化任务...</div>;

  const handleCancel = () => {
    setJob({
      ...job,
      status: 'CANCELLED',
      logs: [
        ...job.logs,
        {
          timestamp: new Date().toLocaleTimeString(),
          role: 'system',
          level: 'warn',
          message: '用户已取消当前任务。注意：在途 API 调用费用仍可能被供应商计费。',
        },
      ],
    });
  };

  const isCompleted = job.status === 'COMPLETED';

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-100 text-purple-800">
              阶段二
            </span>
            <h1 className="text-xl font-bold text-slate-900">命题任务监控与多角色执行看板</h1>
          </div>
          <p className="text-sm text-slate-500">
            按槽位调度 Celery 异步队列，执行命题、独立盲解、规则与数学校验、有限修订。
          </p>
        </div>

        <div className="flex items-center gap-3">
          {!isCompleted && job.status !== 'CANCELLED' && (
            <>
              <button
                onClick={() => setIsPaused(!isPaused)}
                className="px-3.5 py-2 border border-slate-300 hover:bg-slate-100 text-slate-700 font-semibold text-xs rounded-xl flex items-center gap-1.5 transition"
              >
                {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
                <span>{isPaused ? '继续任务' : '暂停调度'}</span>
              </button>
              <button
                onClick={handleCancel}
                className="px-3.5 py-2 border border-rose-200 hover:bg-rose-50 text-rose-700 font-semibold text-xs rounded-xl flex items-center gap-1.5 transition"
              >
                <XCircle className="w-3.5 h-3.5" />
                <span>取消任务</span>
              </button>
            </>
          )}

          {isCompleted && (
            <button
              onClick={onGoToEditor}
              className="px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-sm rounded-xl flex items-center gap-2 shadow-sm transition"
            >
              <span>进入命题编辑工作台</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Metrics Counters */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-slate-500 font-medium">任务完成进度</div>
            <div className="text-xl font-bold text-slate-900 mt-0.5">
              {job.completed_slots} / {job.total_slots} 题
            </div>
            <div className="text-[11px] text-slate-400">真实槽位状态变迁</div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <Zap className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-slate-500 font-medium">累计 Token 用量</div>
            <div className="text-xl font-bold text-slate-900 mt-0.5">
              {job.tokens_used.toLocaleString()}
            </div>
            <div className="text-[11px] text-slate-400">DeepSeek 官方 API</div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <Coins className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-slate-500 font-medium">预估实时费用</div>
            <div className="text-xl font-bold text-slate-900 mt-0.5">
              ¥ {job.estimated_cost_cny.toFixed(2)}
            </div>
            <div className="text-[11px] text-slate-400">严格预算控制防失控</div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-slate-500 font-medium">当前运行状态</div>
            <div className="text-lg font-bold text-slate-900 mt-0.5 flex items-center gap-1.5">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  job.status === 'RUNNING'
                    ? 'bg-purple-500 animate-pulse'
                    : job.status === 'COMPLETED'
                    ? 'bg-emerald-500'
                    : 'bg-rose-500'
                }`}
              ></span>
              {job.status === 'RUNNING' ? '流水线运行中' : job.status === 'COMPLETED' ? '已全部完成' : '已取消'}
            </div>
            <div className="text-[11px] text-slate-400">Celery + RabbitMQ</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: Slot Matrix */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center justify-between">
            <span>题目槽位生命周期矩阵 (Slot Matrix)</span>
            <span className="text-xs font-normal text-slate-500">
              命题 → 独立盲解 → 规则数学校验 → 有限修订
            </span>
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {job.slots.map((slot) => (
              <div
                key={slot.slot_id}
                className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:border-brand-300 transition space-y-2.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-md bg-slate-100 text-slate-700 flex items-center justify-center font-bold text-xs">
                      #{slot.order}
                    </span>
                    <span className="font-bold text-xs text-slate-900 truncate max-w-[150px]">
                      {slot.target_topic}
                    </span>
                  </div>
                  <StatusBadge status={slot.status} />
                </div>

                <div className="flex items-center justify-between text-xs text-slate-500 pt-1 border-t border-slate-100">
                  <span>{slot.cognitive_target}</span>
                  <span className="font-semibold text-slate-700">{formatScoreX100(slot.score_x100)} 分</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Col: Event Log Stream */}
        <div className="bg-slate-900 text-slate-200 p-5 rounded-2xl shadow-md flex flex-col h-[520px]">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
            <h3 className="font-mono text-xs font-bold text-emerald-400 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              实时事件流 (SSE Stream)
            </h3>
            <span className="text-[10px] text-slate-500 font-mono">Hermes Adapter</span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2.5 font-mono text-[11px] pr-1">
            {job.logs.map((l, idx) => (
              <div key={idx} className="leading-relaxed break-words">
                <span className="text-slate-500">[{l.timestamp}] </span>
                <span
                  className={`font-bold ${
                    l.role === 'author'
                      ? 'text-purple-400'
                      : l.role === 'solver'
                      ? 'text-indigo-400'
                      : l.role === 'reviewer'
                      ? 'text-amber-400'
                      : 'text-slate-400'
                  }`}
                >
                  [{l.role}]
                </span>{' '}
                <span className={l.level === 'warn' ? 'text-amber-300' : 'text-slate-200'}>
                  {l.message}
                </span>
              </div>
            ))}
          </div>

          {isCompleted && (
            <div className="mt-3 pt-3 border-t border-slate-800">
              <button
                onClick={onGoToEditor}
                className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2 transition"
              >
                <CheckCircle2 className="w-4 h-4" />
                全卷命题完毕，点击进入编辑工作台
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
