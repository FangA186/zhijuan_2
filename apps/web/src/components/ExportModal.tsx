import React, { useState } from 'react';
import { X, FileText, Download, Check } from 'lucide-react';
import { GeneratedCandidate } from '../types/candidate';
import { ExamSpec } from '../types/spec';
import { makeExamPublicProjection } from '../lib/projection';
import { candidateHasAssets, downloadDocx, downloadJson } from './exportSupport';
import { ExportOptions } from './ExportOptions';
import { ExportPreview } from './ExportPreview';

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
  const hasDiagramAssets = candidates.some(candidateHasAssets);

  const handleDownloadJson = () => downloadJson(exportType === 'student_pdf' ? publicQuestions : candidates, spec.title, exportType === 'student_pdf' ? '学生公开版' : '全量版');

  const handleDownloadDocx = () => downloadDocx(spec, candidates, fontSizePt);

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
          <ExportOptions exportType={exportType} setExportType={setExportType} paperSize={paperSize} setPaperSize={setPaperSize} fontSizePt={fontSizePt} setFontSizePt={setFontSizePt} hasDiagramAssets={hasDiagramAssets} />

          <ExportPreview exportType={exportType} spec={spec} candidates={candidates} />
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
            ) : exportType === 'docx' ? (
              <button
                onClick={handleDownloadDocx}
                disabled={hasDiagramAssets}
                className="px-4 py-2 text-sm font-bold bg-blue-600 hover:bg-blue-700 disabled:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg shadow-sm flex items-center gap-2 transition"
              >
                <Download className="w-4 h-4" />
                下载 Word 试卷 (.doc)
              </button>
            ) : (
              <button
                onClick={handleTriggerPrint}
                disabled={hasDiagramAssets}
                className="px-4 py-2 text-sm font-bold bg-brand-600 hover:bg-brand-700 disabled:hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg shadow-sm flex items-center gap-2 transition"
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
