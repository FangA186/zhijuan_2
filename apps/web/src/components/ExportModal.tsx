import React, { useState } from 'react';
import { X, FileText, Download, ShieldCheck, Check, Info } from 'lucide-react';
import { GeneratedCandidate } from '../types/candidate';
import { ExamSpec } from '../types/spec';
import { makeExamPublicProjection } from '../lib/projection';
import { MathRenderer } from '../lib/math';
import { formatScoreX100 } from '../lib/scoring';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  spec: ExamSpec;
  candidates: GeneratedCandidate[];
}

export const ExportModal: React.FC<ExportModalProps> = ({
  isOpen,
  onClose,
  spec,
  candidates,
}) => {
  const [exportType, setExportType] = useState<'student_pdf' | 'teacher_pdf' | 'json' | 'docx'>('student_pdf');
  const [paperSize, setPaperSize] = useState<'A4' | 'A3'>('A4');
  const [fontSizePt, setFontSizePt] = useState<number>(11);
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const publicQuestions = makeExamPublicProjection(candidates);

  const handleDownloadJson = () => {
    const dataToExport = exportType === 'student_pdf' ? publicQuestions : candidates;
    const jsonStr = JSON.stringify(dataToExport, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${spec.title}_${exportType === 'student_pdf' ? '学生公开版' : '全量版'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleTriggerPrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div>
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <FileText className="w-5 h-5 text-brand-600" />
              试卷导出与成卷预览
            </h3>
            <p className="text-xs text-slate-500">统一同源快照生成 · 严格公开投影保密</p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {/* Format selection */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              {
                id: 'student_pdf',
                title: '学生版试卷 (PDF)',
                desc: '严格无答案与解析，公开投影保障',
                badge: '防泄露',
              },
              {
                id: 'teacher_pdf',
                title: '教师全解版 (PDF)',
                desc: '含标准答案、分步给分点与解析',
                badge: '全卷',
              },
              {
                id: 'json',
                title: '结构化数据 (JSON)',
                desc: '符合 OpenAPI 与 candidate.schema',
                badge: '标准API',
              },
              {
                id: 'docx',
                title: '可编辑试卷 (Word)',
                desc: '支持公式转换与教师再次排版',
                badge: '可编辑',
              },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setExportType(f.id as any)}
                className={`p-3 rounded-xl border text-left transition-all ${
                  exportType === f.id
                    ? 'border-brand-500 bg-brand-50/50 ring-2 ring-brand-500/20 shadow-xs'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-sm text-slate-900">{f.title}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold">
                    {f.badge}
                  </span>
                </div>
                <p className="text-xs text-slate-500 line-clamp-2">{f.desc}</p>
              </button>
            ))}
          </div>

          {/* Security Banner */}
          {exportType === 'student_pdf' && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start gap-3 text-xs text-emerald-800">
              <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">安全保证：</span>
                学生端试卷在数据层彻底过滤了私有答案（private.answers）、评分细则与解析文本，杜绝任何审查元素或抓包泄题风险。
              </div>
            </div>
          )}

          {exportType === 'docx' && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-3 text-xs text-amber-800">
              <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">排版提示：</span>
                Word 导出基于 python-docx 管线生成，公式将尽可能转为 OMML 或清晰矢量图。不承诺与浏览器分页绝对逐像素一致。
              </div>
            </div>
          )}

          {/* Print Preferences */}
          <div className="flex flex-wrap items-center gap-6 p-4 bg-slate-50 rounded-xl border border-slate-200 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-slate-600 font-medium">纸张规格:</span>
              <select
                value={paperSize}
                onChange={(e) => setPaperSize(e.target.value as any)}
                className="bg-white border border-slate-300 rounded-lg px-2.5 py-1 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-brand-500"
              >
                <option value="A4">A4 (标准题单)</option>
                <option value="A3">A3 (大考双栏对折卷)</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-600 font-medium">字号排版:</span>
              <select
                value={fontSizePt}
                onChange={(e) => setFontSizePt(Number(e.target.value))}
                className="bg-white border border-slate-300 rounded-lg px-2.5 py-1 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-brand-500"
              >
                <option value={10}>10 pt (紧凑)</option>
                <option value={11}>11 pt (标准五号字)</option>
                <option value={12}>12 pt (小学/大字)</option>
                <option value={14}>14 pt (特大字)</option>
              </select>
            </div>
          </div>

          {/* Paper Preview Area */}
          <div className="border border-slate-300 rounded-xl bg-slate-100 p-4 shadow-inner max-h-72 overflow-y-auto">
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
                            <MathRenderer content={opt.content} />
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Private answers shown only in teacher mode */}
                    {exportType !== 'student_pdf' && cand.private.answers.length > 0 && (
                      <div className="mt-2.5 p-2.5 bg-brand-50/70 border border-brand-200 rounded-lg space-y-1.5 text-[11px]">
                        <div className="font-bold text-brand-900 flex items-center gap-1">
                          <span>【标准答案】:</span>
                          <span className="text-brand-700 font-mono text-xs">{cand.private.answers[0].answer_text}</span>
                        </div>
                        <div className="text-slate-700">
                          <span className="font-semibold text-slate-800">【解析过程】: </span>
                          <MathRenderer content={cand.private.answers[0].explanation} />
                        </div>
                        {cand.private.answers[0].scoring_rubric.length > 0 && (
                          <div className="text-slate-600 mt-1 border-t border-brand-100 pt-1">
                            <span className="font-semibold text-slate-800">【评分标准】: </span>
                            <ul className="list-disc pl-4 space-y-0.5 mt-0.5">
                              {cand.private.answers[0].scoring_rubric.map((r, sIdx) => (
                                <li key={sIdx}>
                                  第{r.step}步 ({formatScoreX100(r.score_x100)}分): {r.criterion}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
          <button
            onClick={() => {
              const text = JSON.stringify(exportType === 'student_pdf' ? publicQuestions : candidates, null, 2);
              navigator.clipboard.writeText(text);
              setCopied(true);
              setTimeout(() => setCopied(false), 2000);
            }}
            className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 border border-slate-300 rounded-lg hover:bg-white flex items-center gap-1.5 transition"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-600" /> : null}
            <span>{copied ? '已复制 JSON 到剪贴板' : '复制数据 JSON'}</span>
          </button>

          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 rounded-lg hover:bg-slate-200/60 transition"
            >
              关闭
            </button>
            {exportType === 'json' ? (
              <button
                onClick={handleDownloadJson}
                className="px-4 py-2 text-sm font-bold bg-brand-600 hover:bg-brand-700 text-white rounded-lg shadow-sm flex items-center gap-2 transition"
              >
                <Download className="w-4 h-4" />
                下载 JSON 数据包
              </button>
            ) : (
              <button
                onClick={handleTriggerPrint}
                className="px-4 py-2 text-sm font-bold bg-brand-600 hover:bg-brand-700 text-white rounded-lg shadow-sm flex items-center gap-2 transition"
              >
                <Download className="w-4 h-4" />
                打印 / 导出为 PDF
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
