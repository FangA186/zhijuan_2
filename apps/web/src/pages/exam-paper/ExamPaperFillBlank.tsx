import React from 'react';
import { RefreshCw } from 'lucide-react';
import { MathRenderer } from '../../lib/math';
import type { ExamPaperSectionProps } from './ExamPaperSectionProps';

export const ExamPaperFillBlank: React.FC<ExamPaperSectionProps> = ({ singleChoiceQuestions, multipleChoiceQuestions, fillBlankQuestions, fillBlankTotal, viewMode, checkLabel, getSafeAnswerText }) => (
  <>
          {/* ===================== 三、填空题 ===================== */}
          {fillBlankQuestions.length > 0 && (
            <div className="space-y-6 pt-4">
              <div className="font-bold text-base text-slate-900 border-b border-slate-200 pb-2 font-sans flex items-center justify-between">
                <span>
                  {multipleChoiceQuestions.length > 0 ? '三' : '二'}、填空题 (本大题共 {fillBlankQuestions.length} 小题，每小题{' '}
                  {(fillBlankQuestions[0]?.public.score_x100 || 500) / 100} 分，共 {fillBlankTotal} 分)
                </span>
                <span className="text-xs font-normal text-slate-400 print:hidden font-sans">
                  把答案填在题中横线上
                </span>
              </div>

              <div className="space-y-6">
                {fillBlankQuestions.map((cand, idx) => {
                  const privAnswer = cand.private?.answers?.[0];
                  const answerText = getSafeAnswerText(privAnswer, cand.public);
                  const qNumber = singleChoiceQuestions.length + multipleChoiceQuestions.length + idx + 1;

                  return (
                    <div
                      key={cand.public.local_id}
                      className="group relative rounded-xl transition-all hover:bg-slate-50/70 p-2 sm:p-3 -mx-2 sm:-mx-3"
                    >
                      <div className="flex items-start gap-2 text-sm leading-relaxed">
                        <span className="font-bold font-sans shrink-0">{qNumber}.</span>
                        <span className="print:hidden text-[11px] text-slate-600 shrink-0">{checkLabel(cand.public.local_id)}</span>
                        <div className="min-w-0 flex-1">
                          <div className="max-w-full overflow-x-auto print:overflow-visible">
                            <MathRenderer content={cand.public.prompt} />
                          </div>
                        </div>
                      </div>

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

                      {/* 教师详解卷模式 */}
                      {viewMode === 'teacher' && (
                        <div className="mt-3 pl-6 pt-2 text-xs font-sans space-y-1.5 text-slate-700 border-t border-dashed border-slate-200">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded bg-brand-100 text-brand-800 font-bold">
                              参考答案：{answerText}
                            </span>
                          </div>
                          {privAnswer?.explanation && (
                            <div className="p-2.5 bg-brand-50/50 rounded-lg text-slate-700 border border-brand-100/80 leading-relaxed">
                              <span className="font-bold text-brand-900 block mb-1">详细推导：</span>
                              <MathRenderer content={privAnswer.explanation} />
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}


  </>
);
