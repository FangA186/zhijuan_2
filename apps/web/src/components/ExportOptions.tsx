import React from 'react';
import { ShieldCheck, Info } from 'lucide-react';

type ExportType = 'student_pdf' | 'teacher_pdf' | 'json' | 'docx';
interface ExportOptionsProps {
  exportType: ExportType;
  setExportType: (value: ExportType) => void;
  paperSize: 'A4' | 'A3';
  setPaperSize: (value: 'A4' | 'A3') => void;
  fontSizePt: number;
  setFontSizePt: (value: number) => void;
  hasDiagramAssets: boolean;
}
export const ExportOptions: React.FC<ExportOptionsProps> = ({ exportType, setExportType, paperSize, setPaperSize, fontSizePt, setFontSizePt, hasDiagramAssets }) => (
  <>
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

          {hasDiagramAssets && exportType !== 'json' && (
            <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800">
              本轮暂不支持含图试卷的浏览器打印 / PDF 和旧 Word 导出，已禁用这些导出以避免丢图。图示仍会在预览区加载，JSON 可保留图资产引用。
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

  </>
);
