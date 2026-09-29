import React from 'react';
import { ChevronDown, ChevronRight, CheckSquare, MinusSquare, Square, FolderOpen, Folder, FileText } from 'lucide-react';
import { ChapterTreeNode } from '../types/spec';
import { getDescendantTitles } from './chapterTreeUtils';

interface ChapterTreeNodeRowProps {
  node: ChapterTreeNode;
  depth: number;
  expandedNodeIds: Set<string>;
  selectedNodeIds: Set<string>;
  existingTopics: string[];
  existingExcluded: string[];
  externalSelection: boolean;
  onToggleSelect: (node: ChapterTreeNode) => void;
  onToggleExpand: (nodeId: string) => void;
}

export const ChapterTreeNodeRow: React.FC<ChapterTreeNodeRowProps> = (props) => {
  const { node, depth, expandedNodeIds, selectedNodeIds, existingTopics, existingExcluded, externalSelection, onToggleSelect, onToggleExpand } = props;
  const hasChildren = Boolean(node.child_nodes?.length);
  const isExpanded = expandedNodeIds.has(node.id);
  const inTopics = existingTopics.includes(node.title);
  const inExcluded = existingExcluded.includes(node.title);
  const family = hasChildren ? getDescendantTitles(node) : [];
  const selectedCount = family.filter((title) => existingTopics.includes(title)).length;
  const full = inTopics || (family.length > 0 && selectedCount === family.length);
  const partial = selectedCount > 0 && selectedCount < family.length && !full;
  const checked = full || (!externalSelection && selectedNodeIds.has(node.id));
  return (
    <div className="select-none" key={node.id}>
      <div onClick={() => onToggleSelect(node)} className={`group flex items-center justify-between py-1.5 px-2 rounded-xl cursor-pointer transition text-xs ${full ? 'bg-brand-50/80 text-brand-900 font-semibold border border-brand-200/60' : partial ? 'bg-brand-50/40 text-brand-800 border border-brand-100' : 'hover:bg-slate-100/80 text-slate-700 border border-transparent'}`} style={{ paddingLeft: `${depth * 18 + 8}px` }}>
        <div className="flex items-center gap-2 flex-1 min-w-0 pr-2">
          {hasChildren ? <button type="button" onClick={(event) => { event.stopPropagation(); onToggleExpand(node.id); }} className="w-4 h-4 flex items-center justify-center text-slate-400 hover:text-slate-700 shrink-0">{isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}</button> : <span className="w-4 h-4 shrink-0" />}
          <div className="shrink-0">{checked ? <CheckSquare className="w-4 h-4 text-brand-600" /> : partial ? <MinusSquare className="w-4 h-4 text-brand-600" /> : <Square className="w-4 h-4 text-slate-300 group-hover:text-slate-400" />}</div>
          {depth === 0 ? (isExpanded ? <FolderOpen className="w-3.5 h-3.5 text-amber-500 shrink-0" /> : <Folder className="w-3.5 h-3.5 text-amber-500 shrink-0" />) : <FileText className="w-3 h-3 text-slate-400 shrink-0" />}
          <span className={`truncate ${full ? 'font-bold text-brand-700' : partial ? 'font-semibold text-brand-800' : depth === 0 ? 'font-bold text-slate-900' : depth === 1 ? 'font-medium text-slate-800' : 'text-slate-600'}`}>{node.title}</span>
          {full ? <span className="px-1.5 py-0.2 rounded-sm bg-brand-600 text-white text-[10px] font-bold shrink-0">已选考查</span> : partial ? <span className="px-1.5 py-0.2 rounded-sm bg-brand-100 text-brand-700 text-[10px] font-medium shrink-0">部分已选</span> : null}
          {inExcluded && <span className="px-1.5 py-0.2 rounded-sm bg-rose-100 text-rose-800 text-[10px] font-bold shrink-0">已排除</span>}
        </div>
        <div className="flex items-center gap-1 shrink-0">{full ? <span className="text-[11px] text-brand-600 font-medium opacity-80 group-hover:opacity-100">点击取消</span> : <span className="text-[11px] text-slate-400 opacity-0 group-hover:opacity-100">点击勾选</span>}</div>
      </div>
      {hasChildren && isExpanded && <div className="space-y-0.5 mt-0.5">{node.child_nodes!.map((child) => <ChapterTreeNodeRow key={child.id} {...props} node={child} depth={depth + 1} />)}</div>}
    </div>
  );
};
