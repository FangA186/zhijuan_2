import React from 'react';
import { Tag } from 'lucide-react';
import { PASSAGE_THEME_PRESETS } from './englishPresets';

interface EnglishThemePanelProps {
  selectedThemes: string[];
  themePrompt: string;
  onToggleTheme: (theme: string) => void;
  onChangePrompt: (prompt: string) => void;
}

export const EnglishThemePanel: React.FC<EnglishThemePanelProps> = ({ selectedThemes, themePrompt, onToggleTheme, onChangePrompt }) => (
  <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs space-y-4">
    <div className="flex items-center gap-2">
      <div className="w-7 h-7 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs"><Tag className="w-4 h-4" /></div>
      <div><div className="text-sm font-bold text-slate-900">语篇题材偏好与命题提示词</div><div className="text-xs text-slate-500">指定完型与阅读理解文章的主题方向，以及书面表达情境要求</div></div>
    </div>
    <div className="space-y-1.5">
      <div className="text-xs text-slate-500">选择考查题材偏好（点击勾选）：</div>
      <div className="flex flex-wrap gap-2">
        {PASSAGE_THEME_PRESETS.map((theme) => {
          const selected = selectedThemes.includes(theme);
          return <button key={theme} type="button" onClick={() => onToggleTheme(theme)} className={`px-3 py-1.5 text-xs rounded-xl border transition-all cursor-pointer ${selected ? 'bg-indigo-600 text-white border-indigo-600 font-semibold shadow-2xs' : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200 hover:border-slate-300'}`}>{selected ? '✓ ' : '+ '}{theme}</button>;
        })}
      </div>
    </div>
    <div className="space-y-1.5">
      <label className="block text-xs font-semibold text-slate-700">阅读与写作具体要求描述（选填）：</label>
      <textarea rows={2} value={themePrompt} onChange={(e) => onChangePrompt(e.target.value)} placeholder="例如：完形填空为校园互助温情记叙文；阅读C篇为介绍中国天宫空间站的科技说明文；书面表达为给外国留学生写一封介绍端午节的邀请信..." className="w-full border border-slate-300 rounded-xl p-3 text-xs text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden leading-relaxed" />
    </div>
  </div>
);
