import React from 'react';
import { BookOpen, Check, Plus, X } from 'lucide-react';

interface ChinesePoetryPanelProps {
  poetryList: string[];
  presets: string[];
  input: string;
  setInput: (value: string) => void;
  onAdd: (item: string) => void;
  onRemove: (item: string) => void;
  onAddCustom: () => void;
  onClear: () => void;
}

export const ChinesePoetryPanel: React.FC<ChinesePoetryPanelProps> = ({ poetryList, presets, input, setInput, onAdd, onRemove, onAddCustom, onClear }) => (
  <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs space-y-4">
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs"><BookOpen className="w-4 h-4" /></div>
        <div>
          <div className="text-sm font-bold text-slate-900">指定古诗文篇目（默写与文言考查）</div>
          <div className="text-xs text-slate-500">AI 将严格在您指定的篇目内出默写填空与诗文鉴赏题，不超范围考查</div>
        </div>
      </div>
      {poetryList.length > 0 && <button type="button" onClick={onClear} className="text-xs text-slate-400 hover:text-rose-600 transition cursor-pointer">清空已选篇目</button>}
    </div>
    {poetryList.length > 0 ? (
      <div className="space-y-2">
        <div className="text-xs font-semibold text-emerald-800 flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-emerald-600" /><span>已选入本次考查篇目 (共 {poetryList.length} 篇)：</span></div>
        <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto p-2 bg-emerald-50/40 rounded-xl border border-emerald-200/70">
          {poetryList.map((item) => <span key={item} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white text-emerald-900 text-xs font-semibold border border-emerald-300 shadow-2xs group"><span>{item}</span><button type="button" onClick={() => onRemove(item)} className="text-slate-400 hover:text-rose-600 transition cursor-pointer" title="移除"><X className="w-3.5 h-3.5" /></button></span>)}
        </div>
      </div>
    ) : <div className="px-4 py-3 rounded-xl bg-slate-50 border border-dashed border-slate-200 text-xs text-slate-400 text-center">尚未指定篇目，请在下方点击课标推荐篇目，或手动输入添加（未指定时 AI 将随机精选课标必背篇目）</div>}
    <div className="space-y-2">
      <div className="text-xs font-semibold text-slate-600">课标必背高频推荐篇目（点击即可快速添加/移除）：</div>
      <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto p-1">
        {presets.map((preset) => {
          const isSelected = poetryList.includes(preset);
          return <button key={preset} type="button" onClick={() => (isSelected ? onRemove(preset) : onAdd(preset))} className={`px-2.5 py-1 text-xs rounded-lg border transition-all cursor-pointer ${isSelected ? 'bg-emerald-600 text-white border-emerald-600 font-bold shadow-2xs' : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200 hover:border-slate-300'}`}>{preset}</button>;
        })}
      </div>
    </div>
    <div className="flex items-center gap-2 pt-1">
      <input type="text" value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); onAddCustom(); } }} placeholder="手动输入任意古诗文篇目（支持以逗号分隔输入多个，如：马说，过零丁洋）..." className="flex-1 border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden" />
      <button type="button" onClick={onAddCustom} className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl transition flex items-center gap-1 shrink-0 cursor-pointer"><Plus className="w-3.5 h-3.5" /><span>添加</span></button>
    </div>
  </div>
);
