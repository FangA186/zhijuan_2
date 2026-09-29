import React from 'react';
import { formatScoreX100 } from '../../lib/scoring';
import { AnswerScoring } from '../../components/AnswerScoring';
import { CheckCircle2, RefreshCw } from 'lucide-react';
import { MathRenderer } from '../../lib/math';
import type { ExamPaperSectionProps } from './ExamPaperSectionProps';

export const ExamPaperSolution: React.FC<ExamPaperSectionProps> = ({ singleChoiceQuestions, multipleChoiceQuestions, fillBlankQuestions, solutionQuestions, solutionTotal, viewMode, checkLabel }) => (
  <>
          {/* ===================== 四、解答与证明题 ===================== */}
          {solutionQuestions.length > 0 && (
            <div className="space-y-8 pt-4">
              <div className="font-bold text-base text-slate-900 border-b border-slate-200 pb-2 font-sans flex items-center justify-between">
                <span>
                  {multipleChoiceQuestions.length > 0 ? '四' : '三'}、解答与证明题 (本大题共 {solutionQuestions.length} 小题，共 {solutionTotal} 分)
                </span>
                <span className="text-xs font-normal text-slate-400 print:hidden font-sans">
                  解答应写出文字说明、证明过程或演算步骤
                </span>
              </div>

              <div className="space-y-8">
                {solutionQuestions.map((cand, idx) => {
                  const privAnswer = cand.private?.answers?.[0];
                  const qNumber =
                    singleChoiceQuestions.length +
                    multipleChoiceQuestions.length +
                    fillBlankQuestions.length +
                    idx +
                    1;
                  const scoreDisplay = formatScoreX100(cand.public.score_x100);

                  return (
                    <div
                      key={cand.public.local_id}
                      className="group relative rounded-xl transition-all hover:bg-slate-50/70 p-2 sm:p-3 -mx-2 sm:-mx-3 space-y-3"
                    >
                      <div className="flex items-start gap-2 text-sm leading-relaxed">
                        <span className="font-bold font-sans shrink-0">{qNumber}.</span>
                        <span className="print:hidden text-[11px] text-slate-600 shrink-0">{checkLabel(cand.public.local_id)}</span>
                        <div className="min-w-0 flex-1">
                          <div className="max-w-full overflow-x-auto print:overflow-visible">
                            <MathRenderer content={cand.public.prompt} />
                          </div>
                          <span className="text-xs text-slate-500 font-sans ml-1">
                            ({scoreDisplay}分)
                          </span>
                        </div>
                      </div>

                      {/* 学生作答空白框（学生模式） */}
                      {viewMode === 'student' && (
                        <div className="w-full border border-dashed border-slate-300 rounded-lg bg-slate-50/30 min-h-[140px] flex items-end justify-end p-2 text-[10px] text-slate-400 font-sans">
                          作答区（预留作答空间）
                        </div>
                      )}

                      {/* 教师详解卷模式（展开推导过程与采分细则） */}
                      {viewMode === 'teacher' && (
                        <div className="mt-3 pl-6 pt-3 text-xs font-sans space-y-3 text-slate-700 border-t border-dashed border-slate-200">
                          {privAnswer?.explanation && (
                            <div className="p-3 bg-brand-50/50 rounded-xl border border-brand-100 leading-relaxed">
                              <div className="font-bold text-brand-900 mb-1.5 flex items-center gap-1.5">
                                <CheckCircle2 className="w-4 h-4 text-brand-600" />
                                参考解题步骤：
                              </div>
                              <div className="max-w-full overflow-x-auto print:overflow-visible">
                                <MathRenderer content={privAnswer.explanation} />
                              </div>
                            </div>
                          )}

                          <AnswerScoring question={cand.public} answer={privAnswer} />
                        </div>
                      )}

                      {/* 悬浮换一题 */}
                      <div className="absolute top-2 right-2 print:hidden flex items-center gap-1.5 bg-white/90 shadow-2xs border border-slate-200 rounded-lg p-1">
                        <button
                          type="button"
                          disabled
                          title="版本化换题尚未启用"
                          className="px-2 py-1 text-xs text-slate-600 rounded flex items-center gap-1 opacity-60 cursor-not-allowed"
                        >
                          <RefreshCw className="w-3 h-3" />
                          <span>换一题（版本化换题尚未启用）</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}


  </>
);
