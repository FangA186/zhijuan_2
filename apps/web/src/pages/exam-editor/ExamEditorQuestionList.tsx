import React from 'react';
import { GeneratedCandidate } from '../../types/candidate';
import { ValidationRecord } from '../../types/validation';
import { StatusBadge } from '../../components/StatusBadge';
import { formatScoreX100 } from '../../lib/scoring';

interface Props {
  candidates: GeneratedCandidate[];
  validationRecords: Record<string, ValidationRecord>;
  currentId: string;
  onSelect: (id: string) => void;
}

export const ExamEditorQuestionList: React.FC<Props> = ({ candidates, validationRecords, currentId, onSelect }) => (
  <div className="lg:col-span-3 bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-3 max-h-[820px] overflow-y-auto">
    <div className="flex items-center justify-between border-b border-slate-100 pb-2">
      <span className="font-bold text-xs text-slate-700">题目目录与状态</span>
      <span className="text-[11px] text-slate-400">共 {candidates.length} 题</span>
    </div>
    <div className="space-y-1.5">
      {candidates.map((cand, idx) => {
        const val = validationRecords[cand.public.local_id];
        const isSelected = cand.public.local_id === currentId;
        return (
          <button key={cand.public.local_id} onClick={() => onSelect(cand.public.local_id)}
            className={`w-full p-2.5 rounded-xl border text-left transition-all flex items-center justify-between gap-2 ${isSelected ? 'border-brand-500 bg-brand-50/60 ring-2 ring-brand-500/20 shadow-xs' : 'border-slate-200 hover:border-slate-300 bg-white'}`}>
            <div className="flex items-center gap-2 overflow-hidden">
              <span className={`w-6 h-6 rounded-md flex items-center justify-center font-bold text-xs shrink-0 ${isSelected ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'}`}>{idx + 1}</span>
              <div className="truncate">
                <div className="text-xs font-semibold text-slate-900 truncate">
                  {cand.public.kind === 'single_choice' ? '单选' : cand.public.kind === 'solution' ? '解答' : '填空'}:
                  {' '}{cand.public.prompt[0]?.type === 'text' ? cand.public.prompt[0].text.slice(0, 16) : '数学题'}
                </div>
                <div className="text-[10px] text-slate-400">{formatScoreX100(cand.public.score_x100)} 分</div>
              </div>
            </div>
            <StatusBadge status={val?.overall_status || 'PASS'} />
          </button>
        );
      })}
    </div>
  </div>
);
