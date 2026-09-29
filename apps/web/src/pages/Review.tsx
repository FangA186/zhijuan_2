import React, { useEffect, useState } from 'react';
import { CheckCircle2, Send } from 'lucide-react';
import { GeneratedCandidate } from '../types/candidate';
import { AdjudicationRecord, ValidationRecord } from '../types/validation';
import { ExamSpec } from '../types/spec';
import { api } from '../lib/api';
import { formatScoreX100, validateScoreBalance } from '../lib/scoring';
import { ReviewChecklist } from './review/ReviewChecklist';
import { ReviewIntegrity } from './review/ReviewIntegrity';

interface ReviewProps {
  onPublishSuccess: () => void;
  spec: ExamSpec;
}

export const Review: React.FC<ReviewProps> = ({ onPublishSuccess, spec }) => {
  const [candidates, setCandidates] = useState<GeneratedCandidate[]>([]);
  const [validationRecords, setValidationRecords] = useState<Record<string, ValidationRecord>>({});
  const [adjudications, setAdjudications] = useState<Record<string, AdjudicationRecord>>({});
  const [reviewReason, setReviewReason] = useState<Record<string, string>>({});
  const [reviewerName, setReviewerName] = useState('张老师 (学科带头人)');
  const [isPublished, setIsPublished] = useState(false);
  const [publishError, setPublishError] = useState<string | null>(null);

  useEffect(() => { void loadData(); }, []);
  const loadData = async () => {
    setCandidates(await api.getCandidates());
    setValidationRecords(await api.getValidationRecords());
    setAdjudications(await api.getAdjudications());
  };

  let passCount = 0;
  let reviewCount = 0;
  let failCount = 0;
  candidates.forEach(candidate => {
    const status = validationRecords[candidate.public.local_id]?.overall_status || 'PASS';
    if (status === 'FAIL') failCount++;
    else if (status === 'REVIEW' && !adjudications[candidate.public.local_id]) reviewCount++;
    else passCount++;
  });

  const scoreBalance = validateScoreBalance(spec.sections, spec.total_score_x100);
  const canPublish = failCount === 0 && reviewCount === 0 && scoreBalance.isBalanced;
  const handleAdjudicate = async (localId: string, decision: 'ACCEPT' | 'REJECT') => {
    const record: AdjudicationRecord = {
      item_id: localId,
      decision,
      reviewer_name: reviewerName,
      reviewer_role: '学科审核教师',
      reason: reviewReason[localId] || '经核实符合教学考查标准，予以准入。',
      timestamp: new Date().toISOString(),
    };
    await api.submitAdjudication(record);
    setAdjudications(await api.getAdjudications());
  };
  const handlePublish = async () => {
    try {
      setIsPublished(true);
      setPublishError(null);
      await api.publishExam('current', { reviewer_name: reviewerName });
      setTimeout(onPublishSuccess, 1000);
    } catch (err: any) {
      setIsPublished(false);
      setPublishError(err.message || '发布门禁检查未通过');
      alert(`发布失败：${err.message || '请确认所有题目均已通过审核'}`);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <header className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800">阶段四 · 智能质检与定稿</span>
            <h1 className="text-xl font-bold text-slate-900">试卷智能质检与教师终审</h1>
          </div>
          <p className="text-sm text-slate-500">严格把关考点对齐、数学推导与格式规范；如遇需教师确认的题目，请签署审核意见后定稿发布。</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <button onClick={handlePublish} disabled={!canPublish || isPublished}
            className={`px-6 py-2.5 rounded-xl font-bold text-sm flex items-center gap-2 shadow-sm transition ${canPublish && !isPublished ? 'bg-brand-600 hover:bg-brand-700 text-white shadow-brand-500/20' : 'bg-slate-200 text-slate-400 cursor-not-allowed'}`}>
            <Send className="w-4 h-4" /><span>{isPublished ? '正在发布...' : '正式审核通过并定稿'}</span>
          </button>
          {publishError && <span className="text-xs text-rose-500 font-medium">{publishError}</span>}
        </div>
      </header>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Metric label="总题量" value={`${candidates.length} 道`} note={`满分 ${formatScoreX100(spec.total_score_x100)} 分`} />
        <Metric label="智能质检通过" value={`${passCount} 道`} note="满足课标与考查标准" positive />
        <Metric label="待教师核对" value={`${reviewCount} 道`} note="需教师确认与签署意见" warning />
        <Metric label="需修改题目" value={`${failCount} 道`} note="存在分歧，建议返回修改" danger />
      </div>
      <ReviewIntegrity />
      <ReviewChecklist
        candidates={candidates}
        validationRecords={validationRecords}
        adjudications={adjudications}
        reviewerName={reviewerName}
        onReviewerNameChange={setReviewerName}
        reviewReason={reviewReason}
        onReviewReasonChange={(id, reason) => setReviewReason(current => ({ ...current, [id]: reason }))}
        onAdjudicate={handleAdjudicate}
      />
    </div>
  );
};

const Metric: React.FC<{ label: string; value: string; note: string; positive?: boolean; warning?: boolean; danger?: boolean }> = ({ label, value, note, positive, warning, danger }) => (
  <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
    <div className="text-xs text-slate-500 font-medium">{label}</div>
    <div className={`text-2xl font-bold mt-1 ${positive ? 'text-emerald-600' : warning ? 'text-amber-600' : danger ? 'text-rose-600' : 'text-slate-900'}`}>{value}</div>
    <div className={`text-[11px] mt-0.5 flex items-center gap-1 ${positive ? 'text-emerald-700' : warning ? 'text-amber-700' : danger ? 'text-rose-700' : 'text-slate-400'}`}>
      {positive && <CheckCircle2 className="w-3.5 h-3.5" />}{note}
    </div>
  </div>
);
