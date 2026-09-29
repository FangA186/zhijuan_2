import React from 'react';
import { Check } from 'lucide-react';
import { ReferenceTemplate, REFERENCE_TEMPLATES } from './examReferenceTemplates';

export const ExamTemplatePresetsPanel: React.FC<{ onApply: (template: ReferenceTemplate) => void }> = ({ onApply }) => (
  <div className="space-y-3">
    {REFERENCE_TEMPLATES.map((template) => <div key={template.id} className="p-4 rounded-2xl border border-slate-200 hover:border-brand-500 hover:bg-brand-50/20 bg-white transition space-y-3 group">
      <div className="flex items-center justify-between"><div className="flex items-center gap-2"><span className="font-bold text-sm text-slate-900 group-hover:text-brand-900">{template.name}</span><span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-brand-100 text-brand-700">{template.badge}</span></div><div className="text-xs font-bold text-slate-500">{template.duration_minutes} 分钟 · 满分 {template.total_score} 分</div></div>
      <p className="text-xs text-slate-500 leading-relaxed">{template.description}</p>
      <div className="bg-slate-50 p-2.5 rounded-xl text-xs text-slate-600 space-y-1">{template.sections.map((section, index) => <div key={index} className="flex justify-between"><span>{section.title}</span><span className="text-slate-400">{section.count} 题</span></div>)}</div>
      <div className="flex justify-end pt-1"><button type="button" onClick={() => onApply(template)} className="px-4 py-1.5 bg-slate-900 hover:bg-brand-600 text-white font-bold text-xs rounded-xl transition cursor-pointer flex items-center gap-1"><Check className="w-3.5 h-3.5" /><span>套用该模板结构</span></button></div>
    </div>)}
  </div>
);
