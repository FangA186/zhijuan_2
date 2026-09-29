import React from 'react';
import { AnswerScoring } from './AnswerScoring';
import { GeneratedCandidate } from '../types/candidate';
import { ExamSpec } from '../types/spec';
import { MathRenderer } from '../lib/math';
import { formatScoreX100 } from '../lib/scoring';
import { getSafeAnswerText } from './exportSupport';

type ExportType = 'student_pdf' | 'teacher_pdf' | 'json' | 'docx';
export const ExportPreview: React.FC<{ exportType: ExportType; spec: ExamSpec; candidates: GeneratedCandidate[] }> = ({ exportType, spec, candidates }) => (
  <>
          {/* Paper Preview Area */}
          <div className="border border-slate-300 rounded-xl bg-slate-100 p-4 shadow-inner max-h-72 overflow-y-auto">
            {exportType === 'json' ? (
              <div className="bg-slate-950 text-emerald-400 p-4 rounded-lg font-mono text-[11px] overflow-x-auto">
                <pre className="whitespace-pre-wrap break-all leading-relaxed">
                  {JSON.stringify(
                    {
                      exam_id: (spec as any).exam_id || 'current',
                      title: spec.title,
                      total_score_x100: spec.total_score_x100,
                      grade: spec.grade_label,
                      subject: spec.subject_label,
                      questions: candidates,
                    },
                    null,
                    2
                  )}
                </pre>
              </div>
            ) : (
              <div className="bg-white p-6 rounded-lg shadow-sm border border-slate-200 max-w-2xl mx-auto space-y-4">
                {/* Paper Title Header */}
                <div className="text-center border-b border-slate-200 pb-4">
                  <h1 className="text-lg font-bold text-slate-900 tracking-wide">{spec.title}</h1>
                  <p className="text-xs text-slate-500 mt-1">
                    考试时长: {spec.duration_minutes || 90} 分钟 | 满分: {formatScoreX100(spec.total_score_x100)} 分
                    {exportType === 'student_pdf' ? ' (学生作答卷)' : ' (教师参考及评分细则)'}
                  </p>
                </div>

                {/* Questions preview */}
                <div className="space-y-4 text-xs">
                  {candidates.map((cand, idx) => (
                    <div key={cand.public.local_id} className="pb-3 border-b border-slate-100 last:border-0">
                      <div className="flex items-start gap-2 font-medium text-slate-900 mb-1.5">
                        <span className="font-bold shrink-0">{idx + 1}.</span>
                        <div className="flex-1">
                          <MathRenderer content={cand.public.prompt} />
                        </div>
                        <span className="text-slate-400 font-normal shrink-0">({formatScoreX100(cand.public.score_x100)}分)</span>
                      </div>

                      {/* Options if choice */}
                      {cand.public.options && cand.public.options.length > 0 && (
                        <div className="grid grid-cols-2 gap-2 pl-4 mt-2">
                          {cand.public.options.map((opt) => (
                            <div key={opt.id} className="flex items-center gap-1.5 text-slate-700">
                              <span className="font-bold">{opt.label || opt.id.replace('opt_', '')}.</span>
                              <MathRenderer content={opt.content || (opt as any).text} />
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Private answers shown only in teacher mode and Word preview */}
                      {exportType !== 'student_pdf' && cand.private?.answers && cand.private.answers.length > 0 && (() => {
                        const ans = cand.private.answers[0];
                        if (!ans) return null;
                        const answerText = getSafeAnswerText(ans, cand);

                        return (
                          <div className="mt-2.5 p-2.5 bg-brand-50/70 border border-brand-200 rounded-lg space-y-1.5 text-[11px]">
                            <div className="font-bold text-brand-900 flex items-center gap-1">
                              <span>【标准答案】:</span>
                              <span className="text-brand-700 font-mono text-xs">{answerText}</span>
                            </div>
                            {ans.explanation && (
                              <div className="text-slate-700">
                                <span className="font-semibold text-slate-800">【解析过程】: </span>
                                <MathRenderer content={ans.explanation} />
                              </div>
                            )}
                            <AnswerScoring question={cand.public} answer={ans} />
                          </div>
                        );
                      })()}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
  </>
);
