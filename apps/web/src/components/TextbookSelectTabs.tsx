import React from 'react';
import { Layers, Link as LinkIcon, Search } from 'lucide-react';
import { TextbookFilterMode, TextbookSelectTab } from './textbookSelectionTypes';

interface TextbookSelectTabsProps {
  activeTab: TextbookSelectTab;
  onTabChange: (tab: TextbookSelectTab) => void;
  filterMode: TextbookFilterMode;
  onFilterModeChange: (mode: TextbookFilterMode) => void;
}

const TABS: Array<{ id: TextbookSelectTab; title: string; icon: React.ReactNode }> = [
  { id: 'cascade', title: '级联筛选 (学段/学科/版本)', icon: <Layers className="w-3.5 h-3.5" /> },
  { id: 'search', title: '关键字快速搜书', icon: <Search className="w-3.5 h-3.5" /> },
  { id: 'url', title: '粘贴网页 URL 解析', icon: <LinkIcon className="w-3.5 h-3.5" /> },
];

export const TextbookSelectTabs: React.FC<TextbookSelectTabsProps> = ({ activeTab, onTabChange, filterMode, onFilterModeChange }) => (
  <div className="px-6 py-2.5 border-b border-slate-200 flex items-center justify-between bg-white gap-4 flex-wrap">
    <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl">
      {TABS.map((tab) => <button key={tab.id} type="button" onClick={() => onTabChange(tab.id)} className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${activeTab === tab.id ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'}`}>{tab.icon}<span>{tab.title}</span></button>)}
    </div>
    <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-xs font-medium">
      <button type="button" onClick={() => onFilterModeChange('visible')} className={`px-2.5 py-1 rounded-lg transition ${filterMode === 'visible' ? 'bg-emerald-600 text-white font-bold shadow-xs' : 'text-slate-600 hover:text-slate-900'}`}>🟢 仅看官网开放</button>
      <button type="button" onClick={() => onFilterModeChange('all')} className={`px-2.5 py-1 rounded-lg transition ${filterMode === 'all' ? 'bg-indigo-600 text-white font-bold shadow-xs' : 'text-slate-600 hover:text-slate-900'}`}>🌐 显示全库全部 (3209)</button>
    </div>
  </div>
);
