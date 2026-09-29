import React from 'react';
import { FileText, FileUp } from 'lucide-react';
import { ExamSection } from '../types/spec';

interface ExamStructurePanelProps {
  title: string;
  sections: ExamSection[];
  totalScore: string;
  durationMinutes: number | null;
  onOpenTemplateModal: () => void;
}

export const ExamStructurePanel: React.FC<ExamStructurePanelProps> = ({ title, sections, totalScore, durationMinutes, onOpenTemplateModal }) => {
  const totalQuestions = sections.reduce((sum, section) => sum + section.count, 0);
  return (
    <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs space-y-3.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-brand-100 text-brand-700 flex items-center justify-center font-bold text-xs">
            <FileText className="w-4 h-4" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-900">{title}</div>
            <div className="text-xs text-slate-500">
              当前共 {sections.length} 个大题板块 · 全卷 {totalQuestions} 道题 · 满分 {totalScore} 分 ({durationMinutes || 90} 分钟)
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={onOpenTemplateModal}
          className="px-3.5 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-300 font-semibold text-xs rounded-xl transition flex items-center gap-1.5 cursor-pointer"
        >
          <FileUp className="w-3.5 h-3.5 text-brand-600" />
          <span>更换/上传模板</span>
        </button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
        {sections.map((section, index) => (
          <div key={section.id || index} className="px-3 py-2 rounded-xl bg-slate-50 border border-slate-200/80 text-xs flex items-center justify-between">
            <span className="font-medium text-slate-800 truncate pr-2" title={section.title}>{section.title}</span>
            <span className="text-slate-400 shrink-0 font-medium">{section.count} 题</span>
          </div>
        ))}
      </div>
    </div>
  );
};
