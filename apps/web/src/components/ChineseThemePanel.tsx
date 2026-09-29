import React from 'react';
import { Sparkles } from 'lucide-react';
import { THEME_TAGS } from './chinesePresets';

interface ChineseThemePanelProps {
  themePrompt: string;
  writingPrompt: string;
  onChangeTheme: (value: string) => void;
  onChangeWriting: (value: string) => void;
  onAppendTheme: (tag: string) => void;
}

export const ChineseThemePanel: React.FC<ChineseThemePanelProps> = ({ themePrompt, writingPrompt, onChangeTheme, onChangeWriting, onAppendTheme }) => (
  <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs space-y-4">
    <div className="flex items-center gap-2">
      <div className="w-7 h-7 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs"><Sparkles className="w-4 h-4" /></div>
      <div>
        <div className="text-sm font-bold text-slate-900">选文立意与命题提示词（现代文与写作导向）</div>
        <div className="text-xs text-slate-500">指导 AI 原创现代文阅读文章风格、语用题考查情境与作文命题方向</div>
      </div>
    </div>
    <div className="space-y-1.5">
      <div className="text-xs text-slate-500">推荐考查立意与主题标签（点击填入）：</div>
      <div className="flex flex-wrap gap-1.5">
        {THEME_TAGS.map((tag) => <button key={tag} type="button" onClick={() => onAppendTheme(tag)} className="px-2.5 py-1 text-xs rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-800 border border-indigo-200 transition cursor-pointer">+ {tag}</button>)}
      </div>
    </div>
    <div className="space-y-1.5">
      <label className="block text-xs font-semibold text-slate-700">命题要求与文本风格描述：</label>
      <textarea rows={2} value={themePrompt} onChange={(e) => onChangeTheme(e.target.value)} placeholder="例如：现代文阅读偏好名家文学散文，围绕乡村记忆与时代发展展开；语言文字运用结合校园真实生活情境..." className="w-full border border-slate-300 rounded-xl p-3 text-xs text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden leading-relaxed" />
    </div>
    <div className="space-y-1.5">
      <label className="block text-xs font-semibold text-slate-700">作文专项命题要求（选填）：</label>
      <input type="text" value={writingPrompt} onChange={(e) => onChangeWriting(e.target.value)} placeholder="例如：半命题作文‘在_____中领悟’，注重考查抒情与记叙能力，不少于600字..." className="w-full border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden" />
    </div>
  </div>
);
