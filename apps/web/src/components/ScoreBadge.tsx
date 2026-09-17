import React from 'react';
import { formatScoreX100 } from '../lib/scoring';

interface ScoreBadgeProps {
  score_x100: number;
  className?: string;
}

export const ScoreBadge: React.FC<ScoreBadgeProps> = ({ score_x100, className = '' }) => {
  const formatted = formatScoreX100(score_x100);
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200 ${className}`}
    >
      {formatted} 分
    </span>
  );
};
