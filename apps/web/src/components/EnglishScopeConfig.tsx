import React from 'react';
import { Info } from 'lucide-react';
import { EnglishSpecConfig, ExamSection } from '../types/spec';
import { ExamStructurePanel } from './ExamStructurePanel';
import { EnglishThemePanel } from './EnglishThemePanel';
import { EnglishVocabGallery } from './EnglishVocabGallery';

interface EnglishScopeConfigProps {
  materialId?: string;
  config: EnglishSpecConfig;
  onChange: (config: EnglishSpecConfig) => void;
  sections: ExamSection[];
  totalScore: string;
  durationMinutes: number | null;
  onOpenTemplateModal: () => void;
}

export const EnglishScopeConfig: React.FC<EnglishScopeConfigProps> = ({ materialId, config, onChange, sections, totalScore, durationMinutes, onOpenTemplateModal }) => {
  const selectedThemes = config.passage_themes || [];
  const themePrompt = config.theme_prompt || '';
  const toggleTheme = (theme: string) => onChange({
    ...config,
    passage_themes: selectedThemes.includes(theme) ? selectedThemes.filter((item) => item !== theme) : [...selectedThemes, theme],
  });
  return (
    <div className="space-y-6">
      <div className="p-4 bg-sky-50/80 border border-sky-200/80 rounded-2xl flex items-start gap-3 text-xs text-sky-900">
        <Info className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
        <div className="leading-relaxed"><span className="font-bold">英语学科专属命题模式：</span>英语试卷由<span className="font-semibold underline decoration-sky-400">试卷模板题型大纲</span>（完型/阅读/语法填空/书面表达等）与<span className="font-semibold underline decoration-sky-400">原版教材词汇表</span>驱动。AI 命题时严格限制超纲生词，语篇情境贴合您选定的校本词表范围。</div>
      </div>
      <ExamStructurePanel title="英语试卷大题结构" sections={sections} totalScore={totalScore} durationMinutes={durationMinutes} onOpenTemplateModal={onOpenTemplateModal} />
      <EnglishVocabGallery materialId={materialId} config={config} onChange={onChange} />
      <EnglishThemePanel selectedThemes={selectedThemes} themePrompt={themePrompt} onToggleTheme={toggleTheme} onChangePrompt={(value) => onChange({ ...config, theme_prompt: value })} />
    </div>
  );
};
