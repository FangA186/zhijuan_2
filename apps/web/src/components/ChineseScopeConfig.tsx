import React, { useState } from 'react';
import { Info } from 'lucide-react';
import { ChineseSpecConfig, Stage, ExamSection } from '../types/spec';
import { POETRY_PRESETS_BY_STAGE } from './chinesePresets';
import { ExamStructurePanel } from './ExamStructurePanel';
import { ChinesePoetryPanel } from './ChinesePoetryPanel';
import { ChineseThemePanel } from './ChineseThemePanel';

interface ChineseScopeConfigProps {
  stage: Stage;
  config: ChineseSpecConfig;
  onChange: (config: ChineseSpecConfig) => void;
  sections: ExamSection[];
  totalScore: string;
  durationMinutes: number | null;
  onOpenTemplateModal: () => void;
}

export const ChineseScopeConfig: React.FC<ChineseScopeConfigProps> = ({ stage, config, onChange, sections, totalScore, durationMinutes, onOpenTemplateModal }) => {
  const [customPoetryInput, setCustomPoetryInput] = useState('');
  const poetryList = config.poetry_list || [];
  const themePrompt = config.theme_prompt || '';
  const writingPrompt = config.writing_prompt || '';
  const addPoetry = (item: string) => {
    const value = item.trim();
    if (value && !poetryList.includes(value)) onChange({ ...config, poetry_list: [...poetryList, value] });
  };
  const removePoetry = (item: string) => onChange({ ...config, poetry_list: poetryList.filter((value) => value !== item) });
  const addCustomPoetry = () => {
    if (!customPoetryInput.trim()) return;
    const next = [...poetryList];
    customPoetryInput.split(/[,，\n\s]+/).map((value) => value.trim()).filter(Boolean).forEach((value) => { if (!next.includes(value)) next.push(value); });
    onChange({ ...config, poetry_list: next });
    setCustomPoetryInput('');
  };
  const appendTheme = (tag: string) => {
    const current = themePrompt.trim();
    if (!current) onChange({ ...config, theme_prompt: tag });
    else if (!current.includes(tag)) onChange({ ...config, theme_prompt: `${current}；${tag}` });
  };

  return (
    <div className="space-y-6">
      <div className="p-4 bg-amber-50/80 border border-amber-200/80 rounded-2xl flex items-start gap-3 text-xs text-amber-900">
        <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <div className="leading-relaxed"><span className="font-bold">语文学科专属命题模式：</span>语文试卷不拘泥于教材死板课时，核心依托<span className="font-semibold underline decoration-amber-400">试卷模板题型大纲</span>、<span className="font-semibold underline decoration-amber-400">指定古诗文篇目</span>与<span className="font-semibold underline decoration-amber-400">立意提示词</span>。现代文阅读由 AI 原创命题，名句名篇默写与文言文严格在您指定的篇目内出题。</div>
      </div>
      <ExamStructurePanel title="试卷结构与大题题型" sections={sections} totalScore={totalScore} durationMinutes={durationMinutes} onOpenTemplateModal={onOpenTemplateModal} />
      <ChinesePoetryPanel poetryList={poetryList} presets={POETRY_PRESETS_BY_STAGE[stage] || POETRY_PRESETS_BY_STAGE.junior} input={customPoetryInput} setInput={setCustomPoetryInput} onAdd={addPoetry} onRemove={removePoetry} onAddCustom={addCustomPoetry} onClear={() => onChange({ ...config, poetry_list: [] })} />
      <ChineseThemePanel themePrompt={themePrompt} writingPrompt={writingPrompt} onChangeTheme={(value) => onChange({ ...config, theme_prompt: value })} onChangeWriting={(value) => onChange({ ...config, writing_prompt: value })} onAppendTheme={appendTheme} />
    </div>
  );
};
