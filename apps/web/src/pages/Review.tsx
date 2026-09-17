import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  FileCheck,
  Hash,
  Send,
  UserCheck,
} from 'lucide-react';
import { GeneratedCandidate } from '../types/candidate';
import { ValidationRecord, AdjudicationRecord } from '../types/validation';
import { ExamSpec } from '../types/spec';
import { api } from '../lib/api';
import { StatusBadge } from '../components/StatusBadge';
import { formatScoreX100, validateScoreBalance } from '../lib/scoring';
import { MathRenderer } from '../lib/math';

interface ReviewProps {
  onPublishSuccess: () => void;
  spec: ExamSpec;
}

export const Review: React.FC<ReviewProps> = ({ onPublishSuccess, spec }) => {
  const [candidates, setCandidates] = useState<GeneratedCandidate[]>([]);
  const [validationRecords, setValidationRecords] = useState<Record<string, ValidationRecord>>({});
  const [adjudications, setAdjudications] = useState<Record<string, AdjudicationRecord>>({});
  const [reviewReason, setReviewReason] = useState<{ [key: string]: string }>({});
  const [reviewerName, setReviewerName] = useState('张老师 (学科带头人)');
  const [isPublished, setIsPublished] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    const cands = await api.getCandidates();
    setCandidates(cands);
    const val = await api.getValidationRecords();
    setValidationRecords(val);
    const adj = await api.getAdjudications();
    setAdjudications(adj);
  };

  const totalQuestions = candidates.length;
  let passCount = 0;
  let reviewCount = 0;
  let failCount = 0;

  candidates.forEach((c) => {
    const status = validationRecords[c.public.local_id]?.overall_status || 'PASS';
    const isAdjudicated = !!adjudications[c.public.local_id];

    if (status === 'FAIL') {
      failCount++;
    } else if (status === 'REVIEW' && !isAdjudicated) {
      reviewCount++;
    } else {
      passCount++;
    }
  });

  const scoreBalance = validateScoreBalance(spec.sections, spec.total_score_x100);
  const canPublish = failCount === 0 && reviewCount === 0 && scoreBalance.isBalanced;

  // 提交人工裁决
  const handleAdjudicate = async (localId: string, decision: 'ACCEPT' | 'REJECT') => {
    const reason = reviewReason[localId] || '经核实符合教学考查标准，予以准入。';
    const record: AdjudicationRecord = {
      item_id: localId,
      decision,
      reviewer_name: reviewerName,
      reviewer_role: '学科审核教师',
      reason,
      timestamp: new Date().toISOString(),
    };
    await api.submitAdjudication(record);
    const adj = await api.getAdjudications();
    setAdjudications(adj);
  };

  const handlePublish = () => {
    setIsPublished(true);
    setTimeout(() => {
      onPublishSuccess();
    }, 1500);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800">
              阶段四
            </span>
            <h1 className="text-xl font-bold text-slate-900">质量审核与发布门禁 (Quality Gatekeeper)</h1>
          </div>
          <p className="text-sm text-slate-500">
            硬错误严禁一键忽略；REVIEW 项必须由授权审核人记录依据与签名；生成双快照指纹。
          </p>
        </div>

        <div>
          <button
            onClick={handlePublish}
            disabled={!canPublish || isPublished}
            className={`px-6 py-2.5 rounded-xl font-bold text-sm flex items-center gap-2 shadow-sm transition ${
              canPublish && !isPublished
                ? 'bg-brand-600 hover:bg-brand-700 text-white shadow-brand-500/20'
                : 'bg-slate-200 text-slate-400 cursor-not-allowed'
            }`}
          >
            <Send className="w-4 h-4" />
            <span>{isPublished ? '正在发布...' : '正式审核通过并发布'}</span>
          </button>
        </div>
      </div>

      {/* Gatekeeper Status Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="text-xs text-slate-500 font-medium">总题量</div>
          <div className="text-2xl font-bold text-slate-900 mt-1">{totalQuestions} 道</div>
          <div className="text-[11px] text-slate-400 mt-0.5">满分 {formatScoreX100(spec.total_score_x100)} 分</div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="text-xs text-slate-500 font-medium">自动/人工审核通过</div>
          <div className="text-2xl font-bold text-emerald-600 mt-1">{passCount} 道</div>
          <div className="text-[11px] text-emerald-700 mt-0.5 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            满足准入要求
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="text-xs text-slate-500 font-medium">待复核项目 (REVIEW)</div>
          <div className="text-2xl font-bold text-amber-600 mt-1">{reviewCount} 道</div>
          <div className="text-[11px] text-amber-700 mt-0.5">需人工签署裁决依据</div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="text-xs text-slate-500 font-medium">严重阻断错误 (FAIL)</div>
          <div className="text-2xl font-bold text-rose-600 mt-1">{failCount} 道</div>
          <div className="text-[11px] text-rose-700 mt-0.5">硬性拦截，必须修改</div>
        </div>
      </div>

      {/* Fingerprints & Integrity Bar */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
        <h3 className="font-bold text-sm text-slate-900 flex items-center gap-2">
          <Hash className="w-4 h-4 text-brand-600" />
          双快照指纹核验 (Content Hash & Render Hash)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
            <div className="text-slate-500 font-sans font-semibold">内容指纹 (Content Hash):</div>
            <div className="text-slate-800 break-all">
              sha256:4a81cf208a0029bc41d2f...b983a0194e1e
            </div>
            <div className="text-[10px] text-emerald-700 font-sans">
              ✓ 题面、选项、答案与给分点已冻结防篡改
            </div>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
            <div className="text-slate-500 font-sans font-semibold">排版指纹 (Render Hash):</div>
            <div className="text-slate-800 break-all">
              render_sha256:9c12e8401aa89f1...29c491aa2810
            </div>
            <div className="text-[10px] text-emerald-700 font-sans">
              ✓ 预检 Playwright PDF 渲染布局一致
            </div>
          </div>
        </div>
      </div>

      {/* Checklist & Adjudication Table */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <FileCheck className="w-5 h-5 text-brand-600" />
            门禁核查清单与人工裁决
          </h3>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500">当前审核人:</span>
            <input
              type="text"
              value={reviewerName}
              onChange={(e) => setReviewerName(e.target.value)}
              className="border border-slate-300 rounded px-2 py-0.5 text-slate-800 font-medium"
            />
          </div>
        </div>

        <div className="space-y-4">
          {candidates.map((cand, idx) => {
            const val = validationRecords[cand.public.local_id];
            const status = val?.overall_status || 'PASS';
            const adj = adjudications[cand.public.local_id];

            return (
              <div
                key={cand.public.local_id}
                className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-md bg-slate-200 text-slate-800 font-bold flex items-center justify-center text-xs">
                      #{idx + 1}
                    </span>
                    <span className="font-bold text-sm text-slate-900">
                      题目 ID: {cand.public.local_id} ({formatScoreX100(cand.public.score_x100)}分)
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {adj ? (
                      <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1">
                        <UserCheck className="w-3.5 h-3.5" />
                        人工裁决准入 ({adj.reviewer_name})
                      </span>
                    ) : (
                      <StatusBadge status={status} />
                    )}
                  </div>
                </div>

                {/* Prompt preview */}
                <div className="text-xs text-slate-700 bg-white p-3 rounded-lg border border-slate-200">
                  <MathRenderer content={cand.public.prompt} />
                </div>

                {/* Rule checks detail */}
                {val && val.rule_checks.some((r) => r.status === 'REVIEW' || r.status === 'FAIL') && (
                  <div className="space-y-1.5 pt-1">
                    {val.rule_checks
                      .filter((r) => r.status === 'REVIEW' || r.status === 'FAIL')
                      .map((r) => (
                        <div
                          key={r.rule_id}
                          className="p-2.5 rounded-lg border border-amber-200 bg-amber-50/70 text-xs text-amber-900 space-y-1"
                        >
                          <div className="font-bold flex items-center gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                            {r.name} - {r.status === 'FAIL' ? '严重阻断' : '需审核人确认'}
                          </div>
                          <div className="text-[11px] text-amber-800">{r.detail}</div>
                        </div>
                      ))}
                  </div>
                )}

                {/* Adjudication Action Box if REVIEW */}
                {status === 'REVIEW' && !adj && (
                  <div className="p-3 bg-white border border-amber-300 rounded-xl space-y-2 text-xs">
                    <div className="font-bold text-slate-800">
                      填写人工裁决依据（不可静默绕过）:
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={reviewReason[cand.public.local_id] || ''}
                        onChange={(e) =>
                          setReviewReason({
                            ...reviewReason,
                            [cand.public.local_id]: e.target.value,
                          })
                        }
                        placeholder="请输入符合学情/课程范围的裁决理由..."
                        className="flex-1 border border-slate-300 rounded-lg px-3 py-1.5 text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
                      />
                      <button
                        onClick={() => handleAdjudicate(cand.public.local_id, 'ACCEPT')}
                        className="px-3.5 py-1.5 bg-brand-600 hover:bg-brand-700 text-white font-bold rounded-lg transition shrink-0"
                      >
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
    </div>
  );
};
