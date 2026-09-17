import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, RefreshCw } from 'lucide-react';
import { CheckStatus } from '../types/validation';

interface StatusBadgeProps {
  status: CheckStatus | 'READY' | 'REVIEW_REQUIRED' | 'FAIL' | 'REPAIRING' | 'PENDING' | 'AUTHORING' | 'SOLVING' | 'CHECKING';
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
      label = '通过';
      Icon = CheckCircle2;
      break;
    case 'REVIEW':
    case 'REVIEW_REQUIRED':
      colorCls = 'bg-amber-50 text-amber-700 border-amber-200';
      label = '待人工复核';
      Icon = AlertTriangle;
      break;
    case 'FAIL':
      colorCls = 'bg-rose-50 text-rose-700 border-rose-200';
      label = '未通过';
      Icon = XCircle;
      break;
    case 'REPAIRING':
      colorCls = 'bg-blue-50 text-blue-700 border-blue-200';
      label = '修订中';
      Icon = RefreshCw;
      break;
    case 'AUTHORING':
      colorCls = 'bg-purple-50 text-purple-700 border-purple-200';
      label = '命题中';
      Icon = RefreshCw;
      break;
    case 'SOLVING':
      colorCls = 'bg-indigo-50 text-indigo-700 border-indigo-200';
      label = '独立盲解中';
      Icon = RefreshCw;
      break;
    case 'CHECKING':
      colorCls = 'bg-cyan-50 text-cyan-700 border-cyan-200';
      label = '校验中';
      Icon = RefreshCw;
      break;
    case 'PENDING':
      colorCls = 'bg-slate-100 text-slate-500 border-slate-200';
      label = '排队中';
      break;
  }

  const isSpinning = ['REPAIRING', 'AUTHORING', 'SOLVING', 'CHECKING'].includes(status);
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
