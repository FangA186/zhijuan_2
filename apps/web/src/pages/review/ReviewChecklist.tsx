import React from 'react';
import { AlertTriangle, FileCheck, UserCheck } from 'lucide-react';
import { GeneratedCandidate } from '../../types/candidate';
import { AdjudicationRecord, ValidationRecord } from '../../types/validation';
import { StatusBadge } from '../../components/StatusBadge';
import { formatScoreX100 } from '../../lib/scoring';
import { MathRenderer } from '../../lib/math';

interface ReviewChecklistProps {
  candidates: GeneratedCandidate[];
  validationRecords: Record<string, ValidationRecord>;
  adjudications: Record<string, AdjudicationRecord>;
  reviewerName: string;
  onReviewerNameChange: (name: string) => void;
  reviewReason: Record<string, string>;
  onReviewReasonChange: (localId: string, reason: string) => void;
  onAdjudicate: (localId: string, decision: 'ACCEPT' | 'REJECT') => void;
}

export const ReviewChecklist: React.FC<ReviewChecklistProps> = (props) => (
  <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
    <div className="flex items-center justify-between">
      <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
        <FileCheck className="w-5 h-5 text-brand-600" /> 题目质检清单与教师终审
      </h3>
      <div className="flex items-center gap-2 text-xs">
        <span className="text-slate-500">当前审核人:</span>
        <input type="text" value={props.reviewerName} onChange={e => props.onReviewerNameChange(e.target.value)}
          className="border border-slate-300 rounded px-2 py-0.5 text-slate-800 font-medium" />
      </div>
    </div>
    <div className="space-y-4">
      {props.candidates.map((cand, idx) => {
        const localId = cand.public.local_id;
        const val = props.validationRecords[localId];
        const status = val?.overall_status || 'PASS';
        const adj = props.adjudications[localId];
        return (
          <div key={localId} className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-md bg-slate-200 text-slate-800 font-bold flex items-center justify-center text-xs">#{idx + 1}</span>
                <span className="font-bold text-sm text-slate-900">题目 ID: {localId} ({formatScoreX100(cand.public.score_x100)}分)</span>
              </div>
              {adj ? (
                <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1">
                  <UserCheck className="w-3.5 h-3.5" />人工裁决准入 ({adj.reviewer_name})
                </span>
              ) : <StatusBadge status={status} />}
            </div>
            <div className="text-xs text-slate-700 bg-white p-3 rounded-lg border border-slate-200">
              <MathRenderer content={cand.public.prompt} />
            </div>
            {val && val.rule_checks.some(r => r.status === 'REVIEW' || r.status === 'FAIL') && (
              <div className="space-y-1.5 pt-1">
                {val.rule_checks.filter(r => r.status === 'REVIEW' || r.status === 'FAIL').map(r => (
                  <div key={r.rule_id} className="p-2.5 rounded-lg border border-amber-200 bg-amber-50/70 text-xs text-amber-900 space-y-1">
                    <div className="font-bold flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                      {r.name} - {r.status === 'FAIL' ? '严重阻断' : '需审核人确认'}
                    </div>
                    <div className="text-[11px] text-amber-800">{r.detail}</div>
                  </div>
                ))}
              </div>
            )}
            {status === 'REVIEW' && !adj && (
              <div className="p-3 bg-white border border-amber-300 rounded-xl space-y-2 text-xs">
                <div className="font-bold text-slate-800">填写人工裁决依据（不可静默绕过）:</div>
                <div className="flex gap-2">
                  <input type="text" value={props.reviewReason[localId] || ''}
                    onChange={e => props.onReviewReasonChange(localId, e.target.value)}
                    placeholder="请输入符合学情/课程范围的裁决理由..."
                    className="flex-1 border border-slate-300 rounded-lg px-3 py-1.5 text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden" />
                  <button onClick={() => props.onAdjudicate(localId, 'ACCEPT')}
                    className="px-3.5 py-1.5 bg-brand-600 hover:bg-brand-700 text-white font-bold rounded-lg transition shrink-0">
                    确认准入并签名
                  </button>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  </div>
);
