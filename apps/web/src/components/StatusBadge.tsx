import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, RefreshCw, Hourglass, Ban } from 'lucide-react';
import { CheckStatus } from '../types/validation';

// 与后端任务枚举一致的作业级状态，也用于单题槽位状态
export type JobStatus = 'QUEUED' | 'RUNNING' | 'PAUSED' | 'RECONCILING' | 'COMPLETED' | 'PARTIAL_FAILED' | 'CANCELLED' | 'FAILED';

interface StatusBadgeProps {
  status: CheckStatus | 'READY' | 'REVIEW_REQUIRED' | 'REPAIRING' | 'PENDING' | 'AUTHORING' | 'SOLVING' | 'CHECKING' | JobStatus;
  showIcon?: boolean;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, showIcon = true, size = 'sm' }) => {
  let colorCls = 'bg-slate-100 text-slate-700 border-slate-200';
  let label = status as string;
  let Icon = CheckCircle2;

  switch (status) {
    case 'PASS':
    case 'READY':
      colorCls = 'bg-emerald-50 text-emerald-700 border-emerald-200';
      label = '已就绪';
      Icon = CheckCircle2;
      break;
    case 'REVIEW':
    case 'REVIEW_REQUIRED':
      colorCls = 'bg-amber-50 text-amber-700 border-amber-200';
      label = '待教师复核';
      Icon = AlertTriangle;
      break;
    case 'FAIL':
      colorCls = 'bg-rose-50 text-rose-700 border-rose-200';
      label = '需调整';
      Icon = XCircle;
      break;
    case 'REPAIRING':
      colorCls = 'bg-blue-50 text-blue-700 border-blue-200';
      label = '智能微调中';
      Icon = RefreshCw;
      break;
    case 'AUTHORING':
      colorCls = 'bg-purple-50 text-purple-700 border-purple-200';
      label = '出题构思中';
      Icon = RefreshCw;
      break;
    case 'SOLVING':
      colorCls = 'bg-indigo-50 text-indigo-700 border-indigo-200';
      label = '独立验算中';
      Icon = RefreshCw;
      break;
    case 'CHECKING':
      colorCls = 'bg-cyan-50 text-cyan-700 border-cyan-200';
      label = '课标质检中';
      Icon = RefreshCw;
      break;
    case 'PENDING':
      colorCls = 'bg-slate-100 text-slate-500 border-slate-200';
      label = '等待出题';
      Icon = Hourglass;
      break;
    // 作业级状态：与后端枚举一致，终态不再用“生成中”笼统显示
    case 'QUEUED':
      colorCls = 'bg-amber-50 text-amber-700 border-amber-200';
      label = '排队中';
      Icon = Hourglass;
      break;
    case 'RUNNING':
      colorCls = 'bg-brand-50 text-brand-700 border-brand-200';
      label = '生成中';
      Icon = RefreshCw;
      break;
    case 'PAUSED':
      colorCls = 'bg-slate-100 text-slate-600 border-slate-300';
      label = '已暂停';
      Icon = XCircle;
      break;
    case 'RECONCILING':
      colorCls = 'bg-amber-50 text-amber-800 border-amber-200';
      label = '对账中';
      Icon = AlertTriangle;
      break;
    case 'COMPLETED':
      colorCls = 'bg-emerald-50 text-emerald-700 border-emerald-200';
      label = '已完成，仍需复核';
      Icon = CheckCircle2;
      break;
    case 'PARTIAL_FAILED':
      colorCls = 'bg-rose-50 text-rose-700 border-rose-200';
      label = '部分题目失败';
      Icon = XCircle;
      break;
    case 'CANCELLED':
      colorCls = 'bg-slate-100 text-slate-500 border-slate-300';
      label = '已取消';
      Icon = Ban;
      break;
    case 'FAILED':
      colorCls = 'bg-rose-50 text-rose-700 border-rose-200';
      label = '任务失败';
      Icon = XCircle;
      break;
  }

  const isSpinning = ['REPAIRING', 'AUTHORING', 'SOLVING', 'CHECKING', 'RUNNING'].includes(status);
  const sizeCls = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm';

  return (
    <span
      className={`inline-flex items-center gap-1 font-semibold rounded-full border ${sizeCls} ${colorCls}`}
    >
      {showIcon && <Icon className={`w-3.5 h-3.5 ${isSpinning ? 'animate-spin' : ''}`} />}
      <span>{label}</span>
    </span>
  );
};
