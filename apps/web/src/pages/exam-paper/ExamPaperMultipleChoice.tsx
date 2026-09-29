import React from 'react';
import { AnswerScoring } from '../../components/AnswerScoring';
import { RefreshCw } from 'lucide-react';
import { MathRenderer } from '../../lib/math';
import type { ExamPaperSectionProps } from './ExamPaperSectionProps';

export const ExamPaperMultipleChoice: React.FC<ExamPaperSectionProps> = ({ multipleChoicePartialScoreX100, singleChoiceQuestions, multipleChoiceQuestions, multipleChoiceTotal, viewMode, checkLabel, getSafeAnswerText }) => (
  <>
          {/* ===================== 二、多项选择题 (新高考特有) ===================== */}
          {multipleChoiceQuestions.length > 0 && (
            <div className="space-y-6 pt-4">
              <div className="font-bold text-base text-slate-900 border-b border-slate-200 pb-2 font-sans flex items-center justify-between">
                <span>
                  二、多项选择题 (本大题共 {multipleChoiceQuestions.length} 小题，每小题{' '}
                  {(multipleChoiceQuestions[0]?.public.score_x100 || 500) / 100} 分，共 {multipleChoiceTotal} 分)
                </span>
                <span className="text-xs font-normal text-slate-400 print:hidden font-sans">
                  {multipleChoicePartialScoreX100 === undefined ? '少选计分规则未确认，请教师核对' : `全对按各题满分；少选且无错选得 ${multipleChoicePartialScoreX100 / 100} 分；错选或未答得 0 分`}
                </span>
              </div>

              <div className="space-y-6">
                {multipleChoiceQuestions.map((cand, idx) => {
                  const privAnswer = cand.private?.answers?.[0];
                  const answerText = getSafeAnswerText(privAnswer, cand.public);
                  const qNumber = singleChoiceQuestions.length + idx + 1;

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

                      {/* 选项列表 */}
                      {cand.public.options && cand.public.options.length > 0 && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2.5 pl-6 text-sm">
                          {cand.public.options.map((opt, oIdx) => {
                            const optLabel = String.fromCharCode(65 + oIdx);
                            return (
                              <div key={opt.id} className="min-w-0 flex items-start gap-1.5">
                                <span className="font-bold font-sans text-slate-700 shrink-0">{optLabel}.</span>
                                <div className="min-w-0 max-w-full overflow-x-auto print:overflow-visible">
                                  <MathRenderer content={opt.content || (opt as any).text} />
                                </div>
                              </div>
                            );
                          })}
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

                      {/* 教师详解卷模式 */}
                      {viewMode === 'teacher' && (
                        <div className="mt-3 pl-6 pt-2 text-xs font-sans space-y-1.5 text-slate-700 border-t border-dashed border-slate-200">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded bg-brand-100 text-brand-800 font-bold">
                              参考答案：{answerText}
                            </span>
                          </div>
                          {(privAnswer as any)?.solution && <MathRenderer content={(privAnswer as any).solution} />}
                          <AnswerScoring question={cand.public} answer={privAnswer} />
                          {privAnswer?.explanation && (
                            <div className="p-2.5 bg-brand-50/50 rounded-lg text-slate-700 border border-brand-100/80 leading-relaxed">
                              <span className="font-bold text-brand-900 block mb-1">详细解析与判定：</span>
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
