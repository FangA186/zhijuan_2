import React from 'react';
import { AlertCircle, Check, CheckCircle2, Cpu, RefreshCw, Sparkles, Upload } from 'lucide-react';
import { ExamSection } from '../types/spec';
import { ParsedExamTemplate } from './examTemplateTypes';

interface ExamTemplateUploadPanelProps {
  inputRef: React.RefObject<HTMLInputElement | null>;
  selectedFile: File | null;
  isParsing: boolean;
  parseError: string | null;
  parsedTemplate: ParsedExamTemplate | null;
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onDrop: (event: React.DragEvent) => void;
  onRetry: (file: File) => void;
  onChooseAgain: () => void;
  onReset: () => void;
  onApply: () => void;
}

const questionTypeLabel = (type: ExamSection['question_type']) => {
  const labels: Record<string, string> = { single_choice: '单选题', multiple_choice: '多选题', fill_blank: '填空题', solution: '解答题', true_false: '判断题', essay: '写作题', short_answer: '简答题', material_group: '综合题' };
  return labels[type] || '综合题';
};

export const ExamTemplateUploadPanel: React.FC<ExamTemplateUploadPanelProps> = ({ inputRef, selectedFile, isParsing, parseError, parsedTemplate, onFileChange, onDrop, onRetry, onChooseAgain, onReset, onApply }) => (
  <div className="space-y-4">
    <input ref={inputRef} type="file" accept=".docx,.txt,.json,.md" onChange={onFileChange} className="hidden" />
    {isParsing ? <div className="border-2 border-dashed border-brand-300 bg-brand-50/20 rounded-2xl p-8 text-center transition flex flex-col items-center justify-center gap-3"><div className="w-12 h-12 rounded-2xl bg-brand-100 text-brand-600 flex items-center justify-center animate-spin"><Sparkles className="w-6 h-6" /></div><div><div className="text-sm font-bold text-brand-800">正在智能分析试卷结构与考点分值...</div><div className="text-xs text-slate-400 mt-1">正在提取 Word / 文本大题划分、题型种类、分值与题量</div></div></div>
    : parseError ? <div className="border border-red-200 bg-red-50/60 rounded-2xl p-6 space-y-4"><div className="flex items-start gap-3"><div className="w-9 h-9 rounded-xl bg-red-100 text-red-600 flex items-center justify-center shrink-0"><AlertCircle className="w-5 h-5" /></div><div className="space-y-1 flex-1"><div className="text-sm font-bold text-red-800">试卷模板识别异常</div><div className="text-xs text-red-600 leading-relaxed">{parseError}</div></div></div><div className="flex justify-end gap-2 pt-1"><button type="button" onClick={onChooseAgain} className="px-4 py-2 border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-xl transition cursor-pointer">重新选择文件</button>{selectedFile && <button type="button" onClick={() => onRetry(selectedFile)} className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold rounded-xl transition flex items-center gap-1.5 cursor-pointer"><RefreshCw className="w-3.5 h-3.5" /><span>重试解析</span></button>}</div></div>
    : !parsedTemplate ? <div onDragOver={(event) => event.preventDefault()} onDrop={onDrop} onClick={() => inputRef.current?.click()} className="border-2 border-dashed border-slate-300 hover:border-brand-500 hover:bg-brand-50/20 rounded-2xl p-8 text-center cursor-pointer transition flex flex-col items-center justify-center gap-3 group"><div className="w-12 h-12 rounded-2xl bg-slate-100 group-hover:bg-brand-100 text-slate-500 group-hover:text-brand-600 flex items-center justify-center transition"><Upload className="w-6 h-6" /></div><div><div className="text-sm font-bold text-slate-800 group-hover:text-brand-700">点击或将试卷文件拖拽到此处上传</div><div className="text-xs text-slate-400 mt-1">支持 Word (.docx)、纯文本 (.txt) 或试卷模板</div></div><div className="px-3 py-1 bg-slate-100 rounded-full text-[11px] text-slate-600 font-medium">提取大题题型与分值；请对照原卷核对结果</div></div>
    : <div className="border border-emerald-300 bg-emerald-50/40 rounded-2xl p-5 space-y-4">
      <div className="flex items-center justify-between"><div className="flex items-center gap-2.5"><div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold"><CheckCircle2 className="w-5 h-5" /></div><div><div className="flex items-center gap-2"><span className="text-xs font-bold text-emerald-800">试卷结构已提取</span><span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-700 flex items-center gap-1 border border-blue-200"><Cpu className="w-3 h-3" /> 规则识别 · 待核对</span></div><div className="text-sm font-bold text-slate-900 mt-0.5">{parsedTemplate.fileName}</div></div></div><button type="button" onClick={onReset} className="text-xs text-slate-400 hover:text-slate-600 cursor-pointer">重新上传</button></div>
      {Boolean(parsedTemplate.warnings?.length) && <div className="text-[11px] text-amber-800 bg-amber-50/90 border border-amber-200 px-3 py-2 rounded-xl flex items-center gap-2"><AlertCircle className="w-4 h-4 text-amber-600 shrink-0" /><div>{parsedTemplate.warnings.map((warning, index) => <p key={index}>{warning}</p>)}</div></div>}
      <div className="space-y-2 bg-white p-3.5 rounded-xl border border-emerald-200/80"><div className="text-xs font-bold text-slate-700 flex items-center justify-between"><span>识别结构：全卷共 {parsedTemplate.sections.reduce((a, s) => a + s.count, 0)} 题 · 满分 {parsedTemplate.total_score} 分</span><span className="text-slate-500 font-normal">考试时间：{parsedTemplate.duration_minutes} 分钟</span></div><div className="space-y-1.5 pt-1 max-h-56 overflow-y-auto pr-1">{parsedTemplate.sections.map((section, index) => <div key={index} className="flex items-center justify-between text-xs text-slate-600 bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-100"><div className="flex items-center gap-2 min-w-0 pr-2"><span className="text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0 bg-slate-200 text-slate-700">{questionTypeLabel(section.question_type)}</span><span className="font-medium text-slate-800 truncate" title={section.title}>{section.title}</span></div><div className="text-slate-500 font-mono text-[11px] shrink-0">共 {section.count} 题 · {section.total_score_x100 ? `共 ${(section.total_score_x100 / 100).toFixed(1).replace(/\.0$/, '')} 分` : `每题 ${(section.score_each_x100 / 100).toFixed(1).replace(/\.0$/, '')} 分`}</div></div>)}</div></div>
      <div className="flex justify-end gap-2 pt-1"><button type="button" onClick={onApply} className="px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-xs transition flex items-center gap-1.5 cursor-pointer"><Check className="w-4 h-4" /><span>套用此模板结构出卷</span></button></div>
    </div>}
  </div>
);
