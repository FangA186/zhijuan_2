import React, { useState, useEffect } from 'react';
import { selectionLabels } from '../lib/answerScoring';
import { ExamSpec, QuestionKind } from '../types/spec';
import { GeneratedCandidate } from '../types/candidate';
import { api } from '../lib/api';
import type { ValidationRecord } from '../types/validation';
import { WorkbenchProgressView } from './exam-paper/WorkbenchProgressView';
import { useExamPaperStream } from './exam-paper/useExamPaperStream';
import { ExamPaperPrintView } from './exam-paper/ExamPaperPrintView';

// 题型内部枚举 → 中文题型名（教师界面展示用，不在页面直接堆内部枚举）
export const QUESTION_KIND_LABELS: Record<QuestionKind, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  fill_blank: '填空题',
  solution: '解答题',
  short_answer: '简答题',
  essay: '论述题',
  material_group: '材料综合题组',
};

export function questionKindLabel(kind: QuestionKind | string): string {
  return QUESTION_KIND_LABELS[kind as QuestionKind] ?? String(kind);
}

interface ExamPaperWorkbenchProps {
  spec: ExamSpec;
  candidates: GeneratedCandidate[];
  isGeneratingInitially?: boolean;
  onCandidatesUpdated?: (candidates: GeneratedCandidate[]) => void;
}

export const ExamPaperWorkbench: React.FC<ExamPaperWorkbenchProps> = ({
  spec,
  candidates: initialCandidates,
  isGeneratingInitially = false,
  onCandidatesUpdated,
}) => {
  const [candidates, setCandidates] = useState<GeneratedCandidate[]>(initialCandidates);
  const [isGenerating, setIsGenerating] = useState(isGeneratingInitially);
  const [viewMode, setViewMode] = useState<'student' | 'teacher'>('student');
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [validation, setValidation] = useState<Record<string, ValidationRecord>>({});
  const [paperTitle, setPaperTitle] = useState(spec.title);

  const stream = useExamPaperStream({ isGenerating, setCandidates, setIsGenerating, onCandidatesUpdated });
  const { jobSlots, activeSlotId, currentThinking, tokensUsed, usageStatus, estimatedCost, jobStatus, streamError, setStreamError, connState, recentLogs, generationProgress } = stream;

  useEffect(() => {
    if (isGenerating || candidates.length === 0) return;
    let cancelled = false;
    api.getValidationRecords()
      .then(records => { if (!cancelled) setValidation(records); })
      .catch(() => { if (!cancelled) setValidation({}); });
    return () => { cancelled = true; };
  }, [isGenerating, candidates]);

  const checkLabel = (localId: string): string => {
    const status = validation[localId]?.overall_status;
    if (status === 'FAIL') return '检查失败';
    if (status === 'REVIEW') return '待教师复核';
    if (status === 'PASS') return '服务端检查 PASS，仍需教师复核';
    return '检查状态未知';
  };

  // 手动提前跳过等待并进入试卷：只 GET 当前任务与候选，不重新启动生成
  const handleViewCurrentPaper = async () => {
    try {
      const fresh = await api.getCandidates();
      if (fresh && fresh.length > 0) {
        setCandidates(fresh);
        if (onCandidatesUpdated) onCandidatesUpdated(fresh);
      }
    } catch {}
    // 终态（含 PARTIAL_FAILED 的已完成槽位）可进入排版页；其他状态只能停留在进度页
    if (['COMPLETED', 'PARTIAL_FAILED'].includes(jobStatus)) setIsGenerating(false);
  };

  // 答案安全格式化
  const getSafeAnswerText = (ans: any, question?: GeneratedCandidate['public']): string => {
    if (!ans) return '';
    const labels = selectionLabels(question, ans);
    if (labels.length) return labels.join('、');
    if (typeof ans.answer_text === 'string' && ans.answer_text) return ans.answer_text;
    if (ans.accepted_answers && Array.isArray(ans.accepted_answers)) {
      return ans.accepted_answers
        .map((a: any) => (typeof a === 'string' ? a : a?.value || ''))
        .filter(Boolean)
        .join(' 或 ');
    }
    return '见下方详细推导步骤';
  };

  // 打印试卷
  const handlePrint = () => {
    window.print();
  };

  // ----------------------------------------------------
  // 分类归集题目（全题型无遗漏）
  // ----------------------------------------------------
  const singleChoiceQuestions = candidates.filter((c) => c.public.kind === 'single_choice');
  const multipleChoiceQuestions = candidates.filter((c) => c.public.kind === 'multiple_choice');
  const fillBlankQuestions = candidates.filter((c) => c.public.kind === 'fill_blank');
  const solutionQuestions = candidates.filter((c) => c.public.kind === 'solution' || c.public.kind === 'essay');

  // 计算各大题实际总分
  const singleChoiceTotal = singleChoiceQuestions.reduce((sum, q) => sum + (q.public.score_x100 || 500) / 100, 0);
  const multipleChoiceTotal = multipleChoiceQuestions.reduce((sum, q) => sum + (q.public.score_x100 || 500) / 100, 0);
  const fillBlankTotal = fillBlankQuestions.reduce((sum, q) => sum + (q.public.score_x100 || 500) / 100, 0);
  const solutionTotal = solutionQuestions.reduce((sum, q) => sum + (q.public.score_x100 || 1200) / 100, 0);

  const totalScore = (spec.total_score_x100 / 100).toFixed(0);
  const sectionProps = {
    multipleChoicePartialScoreX100: spec.multiple_choice_partial_score_x100,
    singleChoiceQuestions, multipleChoiceQuestions, fillBlankQuestions, solutionQuestions,
    singleChoiceTotal, multipleChoiceTotal, fillBlankTotal, solutionTotal,
    viewMode, checkLabel, getSafeAnswerText,
  };


  // ----------------------------------------------------
  // 视图 A：AI 实时命题与深度思考驾驶舱
  // ----------------------------------------------------
  if (isGenerating) {
    return (
      <WorkbenchProgressView
        jobId={stream.jobId}
        jobStatus={jobStatus}
        connState={connState}
        tokensUsed={tokensUsed}
        usageStatus={usageStatus}
        estimatedCost={estimatedCost}
        onViewPaper={handleViewCurrentPaper}
        streamError={streamError}
        onRetry={() => { setStreamError('正在重新读取任务状态…'); window.location.reload(); }}
        progress={generationProgress}
        jobSlots={jobSlots}
        activeSlotId={activeSlotId}
        currentThinking={currentThinking}
        recentLogs={recentLogs}
      />
    );
  }

  // ----------------------------------------------------
  // 视图 B：正式 A4 试卷呈现（所见即所得）
  // ----------------------------------------------------
  return (
    <ExamPaperPrintView
      spec={spec} candidates={candidates} viewMode={viewMode} onViewModeChange={setViewMode}
      onPrint={handlePrint} paperTitle={paperTitle} onPaperTitleChange={setPaperTitle}
      totalScore={totalScore} isExportOpen={isExportOpen} onExportOpenChange={setIsExportOpen}
      sectionProps={sectionProps}
    />
  );
};

export default ExamPaperWorkbench;
