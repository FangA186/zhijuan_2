import React from 'react';
import { BookOpen, PlusCircle, Search, Sparkles, Ban } from 'lucide-react';
import { ChapterTreeNode } from '../types/spec';
import { ChapterTreeNodeRow } from './ChapterTreeNodeRow';

interface ChapterTreePanelProps {
  materialId?: string;
  textbookTitle?: string;
  chapters: ChapterTreeNode[];
  filteredChapters: ChapterTreeNode[];
  isLoading: boolean;
  filterKw: string;
  setFilterKw: (value: string) => void;
  stats: { totalChapters: number; totalLessons: number };
  expandedNodeIds: Set<string>;
  selectedNodeIds: Set<string>;
  existingTopics: string[];
  existingExcluded: string[];
  externalSelection: boolean;
  nonQuestionableNotice: string;
  onToggleSelect: (node: ChapterTreeNode) => void;
  onToggleExpand: (id: string) => void;
  onExpandAll: () => void;
  onCollapseAll: () => void;
  onSelectAll: () => void;
  onClearAll: () => void;
  onBatchImportTopics: () => void;
  onBatchImportExcluded: () => void;
  hasExcludedHandler: boolean;
}

export const ChapterTreePanel: React.FC<ChapterTreePanelProps> = (props) => {
  const { materialId, textbookTitle, chapters, filteredChapters, isLoading, filterKw, setFilterKw, stats, expandedNodeIds, selectedNodeIds, existingTopics, existingExcluded, externalSelection, nonQuestionableNotice, onToggleSelect, onToggleExpand, onExpandAll, onCollapseAll, onSelectAll, onClearAll, onBatchImportTopics, onBatchImportExcluded, hasExcludedHandler } = props;
  return (
    <div className="border border-slate-200 rounded-2xl bg-white p-4 shadow-xs space-y-3">
      <div className="flex items-center justify-between gap-3 flex-wrap border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2"><BookOpen className="w-4 h-4 text-brand-600" /><h3 className="text-xs font-bold text-slate-900">教材章节大纲 (点击章节即可直接勾选或取消出卷范围)</h3>{textbookTitle && <span className="px-2 py-0.5 bg-brand-50 text-brand-700 font-semibold rounded-full text-[11px] truncate max-w-xs">{textbookTitle}</span>}</div>
        {chapters.length > 0 && <div className="flex items-center gap-2 text-xs text-slate-500"><span>共 <strong className="text-slate-900">{stats.totalChapters}</strong> 单元/章，<strong className="text-brand-600">{stats.totalLessons}</strong> 小节</span><div className="flex items-center gap-1 border-l border-slate-200 pl-2"><button type="button" onClick={onExpandAll} className="hover:text-slate-900 transition px-1.5 py-0.5 rounded hover:bg-slate-100 text-[11px] cursor-pointer">展开全部</button><span>·</span><button type="button" onClick={onCollapseAll} className="hover:text-slate-900 transition px-1.5 py-0.5 rounded hover:bg-slate-100 text-[11px] cursor-pointer">折叠全部</button></div></div>}
      </div>
      {chapters.length > 0 && <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]"><Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" /><input type="text" value={filterKw} onChange={(event) => setFilterKw(event.target.value)} placeholder="搜索章节、课时名称..." className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-brand-500 focus:outline-hidden" /></div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={onSelectAll} className="px-2.5 py-1.5 bg-brand-50 hover:bg-brand-100 text-brand-700 border border-brand-200 font-bold text-xs rounded-lg transition shadow-2xs flex items-center gap-1 cursor-pointer"><PlusCircle className="w-3.5 h-3.5" /><span>全选全书</span></button>
          {existingTopics.length > 0 && <button type="button" onClick={onClearAll} className="px-2.5 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-200 font-medium text-xs rounded-lg transition cursor-pointer">清空所选</button>}
          {!externalSelection && selectedNodeIds.size > 0 && <><button type="button" onClick={onBatchImportTopics} className="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg transition shadow-xs flex items-center gap-1"><PlusCircle className="w-3.5 h-3.5" /><span>导入为考查范围 ({selectedNodeIds.size})</span></button>{hasExcludedHandler && <button type="button" onClick={onBatchImportExcluded} className="px-2.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-lg transition shadow-xs flex items-center gap-1"><Ban className="w-3.5 h-3.5" /><span>设为不考</span></button>}</>}
        </div>
      </div>}
      <div className="border border-slate-200 rounded-xl max-h-72 overflow-y-auto p-2 bg-slate-50/50">
        {isLoading ? <div className="p-8 text-center text-slate-400 text-xs flex items-center justify-center gap-2"><Sparkles className="w-4 h-4 animate-spin text-brand-600" /><span>正在加载教材章节目录...</span></div> : !materialId ? <div className="p-8 text-center text-slate-400 text-xs">👈 请先在上方选用教材，系统将即刻呈现该书完整大纲目录。</div> : filteredChapters.length === 0 ? <div className="p-8 text-center text-slate-400 text-xs">{filterKw ? '未搜索到匹配章节' : '该教材暂无结构化章节目录'}</div> : <div className="space-y-0.5">{filteredChapters.map((node) => <ChapterTreeNodeRow key={node.id} node={node} depth={0} expandedNodeIds={expandedNodeIds} selectedNodeIds={selectedNodeIds} existingTopics={existingTopics} existingExcluded={existingExcluded} externalSelection={externalSelection} onToggleSelect={onToggleSelect} onToggleExpand={onToggleExpand} />)}</div>}
      </div>
      {nonQuestionableNotice && <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 leading-relaxed">{nonQuestionableNotice}</div>}
    </div>
  );
};
