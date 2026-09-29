import React from 'react';
import { Search } from 'lucide-react';
import { TextbookSummary } from '../types/spec';

interface TextbookSearchPanelProps {
  searchKw: string;
  results: TextbookSummary[];
  onSearch: (keyword: string) => void;
  onChoose: (material: TextbookSummary) => void;
}

export const TextbookSearchPanel: React.FC<TextbookSearchPanelProps> = ({ searchKw, results, onSearch, onChoose }) => (
  <div className="space-y-4">
    <div className="relative"><Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" /><input type="text" value={searchKw} onChange={(event) => onSearch(event.target.value)} placeholder="输入教材名称、学科或版本搜索，例如：数学必修第一册、物理八年级、统编版语文..." className="w-full pl-9 pr-4 py-2.5 border border-slate-300 rounded-xl text-sm text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden" /></div>
    <div className="space-y-2">
      <div className="text-xs text-slate-500">{searchKw ? '搜索结果（最多展示 20 本）：' : '请输入搜索词查找教材...'}</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {results.map((material) => <div key={material.id} className="p-3 border border-slate-200 hover:border-slate-300 rounded-xl bg-white shadow-xs flex items-center justify-between gap-3"><div className="min-w-0 flex-1"><div className="font-bold text-xs text-slate-900 truncate">{material.title}</div><div className="text-[11px] text-slate-500 mt-0.5 truncate">{material.dims?.zxxxd?.name} · {material.dims?.zxxxk?.name} · {material.dims?.zxxbb?.name}</div></div><button type="button" onClick={() => onChoose(material)} className="px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-lg shrink-0 transition">选用</button></div>)}
      </div>
    </div>
  </div>
);
