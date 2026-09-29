import React from 'react';
import { Save, Sparkles, ShieldCheck } from 'lucide-react';
import { GeneratedCandidate } from '../../types/candidate';
import { MathRenderer } from '../../lib/math';
import { formatScoreX100 } from '../../lib/scoring';

interface Props {
  candidate: GeneratedCandidate;
  promptText: string;
  displayedPrompt: GeneratedCandidate['public']['prompt'];
  isStudentView: boolean;
  isSaving: boolean;
  isRegenerating: boolean;
  onPromptChange: (text: string) => void;
  onOptionChange: (optionId: string, text: string) => void;
  onSave: () => void;
  onRegenerate: () => void;
}

export const ExamEditorCanvas: React.FC<Props> = props => {
  const { candidate, promptText, displayedPrompt, isStudentView } = props;
  return (
    <div className="lg:col-span-5 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <span className="font-bold text-sm text-slate-900">题目 #{candidate.public.local_id}</span>
          <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold">{formatScoreX100(candidate.public.score_x100)} 分</span>
        </div>
        {!isStudentView && (
          <div className="flex items-center gap-2">
            <button onClick={props.onRegenerate} disabled={props.isRegenerating}
              className="px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 text-xs font-semibold text-slate-700 flex items-center gap-1 transition"
              title="沿用蓝图槽位目标，重新调用 Agent 命题">
              <Sparkles className={`w-3.5 h-3.5 text-amber-500 ${props.isRegenerating ? 'animate-spin' : ''}`} />
              <span>{props.isRegenerating ? '重构中...' : '重构此题'}</span>
            </button>
            <button onClick={props.onSave} disabled={props.isSaving}
              className="px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-xs font-bold text-white flex items-center gap-1 shadow-xs transition">
              <Save className="w-3.5 h-3.5" /><span>{props.isSaving ? '保存中...' : '保存修改'}</span>
            </button>
          </div>
        )}
      </div>
      {isStudentView && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>当前处于【真实学生端视图】：完全剥离了答案及评分属性，渲染真实卷面。</span>
        </div>
      )}
      <div className="p-4 bg-slate-50/80 rounded-xl border border-slate-200 space-y-2">
        <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">卷面题干预览 (KaTeX LaTeX 实时渲染):</div>
        <div className="text-sm font-medium leading-relaxed"><MathRenderer content={displayedPrompt} /></div>
      </div>
      {!isStudentView && (
        <div className="space-y-1.5">
          <label className="block text-xs font-bold text-slate-700">编辑题干 (支持 $公式$ 或 $$块级公式$$):</label>
          <textarea value={promptText} onChange={e => props.onPromptChange(e.target.value)} rows={3}
            className="w-full border border-slate-300 rounded-xl p-3 text-xs text-slate-800 font-mono leading-relaxed focus:ring-2 focus:ring-brand-500 focus:outline-hidden" />
        </div>
      )}
      {candidate.public.options && candidate.public.options.length > 0 && (
        <div className="space-y-2.5 pt-2">
          <label className="block text-xs font-bold text-slate-700">选项设置 (Options):</label>
          <div className="space-y-2">
            {candidate.public.options.map(opt => {
              const optContent = Array.isArray(opt.content) ? opt.content : typeof (opt as any).text === 'string' ? [{ type: 'text' as const, text: (opt as any).text }] : [];
              const optText = optContent.map(block => block.type === 'text' ? block.text : block.type === 'math' ? `$${block.latex}$` : '').join(' ') || (opt as any).text || '';
              const content = optContent.length > 0 ? optContent : optText;
              return (
                <div key={opt.id} className="p-2.5 rounded-xl border border-slate-200 bg-white flex items-center gap-3 text-xs">
                  <span className="w-6 h-6 rounded-md bg-slate-100 text-slate-800 font-bold flex items-center justify-center shrink-0">{opt.label || opt.id.replace('opt_', '')}</span>
                  <div className="flex-1">
                    {isStudentView ? <MathRenderer content={content} /> : (
                      <input type="text" value={optText} onChange={e => props.onOptionChange(opt.id, e.target.value)}
                        className="w-full border-b border-transparent hover:border-slate-300 focus:border-brand-500 focus:outline-hidden py-1 px-1 text-xs" />
                    )}
                  </div>
                  <div className="shrink-0 text-slate-400"><MathRenderer content={content} /></div>
                </div>
              );
            })}
          </div>
        </div>
      )}
      <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-100">
        <span>预留作答空间: {candidate.public.answer_space_lines} 行</span>
        <span>材料依赖: {candidate.public.material_ids.length > 0 ? '材料综合' : '独立小题'}</span>
      </div>
    </div>
  );
};
