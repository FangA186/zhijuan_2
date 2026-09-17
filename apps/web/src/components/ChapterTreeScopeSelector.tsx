import React, { useState, useEffect, useMemo } from 'react';
import {
  ChevronRight,
  ChevronDown,
  BookOpen,
  PlusCircle,
  Ban,
  CheckSquare,
  Square,
  Search,
  FolderOpen,
  Folder,
  FileText,
  Sparkles,
} from 'lucide-react';
import { ChapterTreeNode } from '../types/spec';
import { api } from '../lib/api';

interface ChapterTreeScopeSelectorProps {
  materialId?: string;
  textbookTitle?: string;
  onAddTopics: (topics: string[]) => void;
  onAddExcludedTopics: (topics: string[]) => void;
  existingTopics: string[];
  existingExcluded: string[];
}

export const ChapterTreeScopeSelector: React.FC<ChapterTreeScopeSelectorProps> = ({
  materialId,
  textbookTitle,
  onAddTopics,
  onAddExcludedTopics,
  existingTopics,
  existingExcluded,
}) => {
  const [chapters, setChapters] = useState<ChapterTreeNode[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedNodeIds, setExpandedNodeIds] = useState<Set<string>>(new Set());
  const [selectedNodeIds, setSelectedNodeIds] = useState<Set<string>>(new Set());
  const [filterKw, setFilterKw] = useState('');

  // 节点 ID 到标题映射
  const [nodeTitleMap, setNodeTitleMap] = useState<Map<string, string>>(new Map());

  // 加载章节树
  useEffect(() => {
    if (!materialId) {
      setChapters([]);
      return;
    }
    loadChapterTree(materialId);
  }, [materialId]);

  const loadChapterTree = async (id: string) => {
    setIsLoading(true);
    try {
      const res = await api.getMaterialChapterTree(id);
      if (res && res.chapters) {
        setChapters(res.chapters);

        // 默认展开前两章，并构建映射
        const newExpanded = new Set<string>();
        const newTitleMap = new Map<string, string>();

        const traverse = (nodes: ChapterTreeNode[], depth = 0) => {
          nodes.forEach((n, idx) => {
            if (depth < 1 || idx < 2) newExpanded.add(n.id);
            if (n.title) newTitleMap.set(n.id, n.title);
            if (n.child_nodes && n.child_nodes.length > 0) {
              traverse(n.child_nodes, depth + 1);
            }
          });
        };

        traverse(res.chapters);
        setExpandedNodeIds(newExpanded);
        setNodeTitleMap(newTitleMap);
        setSelectedNodeIds(new Set());
      } else {
        setChapters([]);
      }
    } catch (e) {
      console.error(e);
      setChapters([]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleExpand = (nodeId: string) => {
    setExpandedNodeIds((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const expandAll = () => {
    const all = new Set<string>();
    const traverse = (nodes: ChapterTreeNode[]) => {
      nodes.forEach((n) => {
        all.add(n.id);
        if (n.child_nodes && n.child_nodes.length > 0) traverse(n.child_nodes);
      });
    };
    traverse(chapters);
    setExpandedNodeIds(all);
  };

  const collapseAll = () => {
    setExpandedNodeIds(new Set());
  };

  const toggleSelectNode = (node: ChapterTreeNode) => {
    setSelectedNodeIds((prev) => {
      const next = new Set(prev);
      const isSelected = next.has(node.id);

      // 联动递归勾选/取消子节点
      const traverse = (n: ChapterTreeNode, select: boolean) => {
        if (select) next.add(n.id);
        else next.delete(n.id);
        if (n.child_nodes && n.child_nodes.length > 0) {
          n.child_nodes.forEach((c) => traverse(c, select));
        }
      };

      traverse(node, !isSelected);
      return next;
    });
  };

  // 批量导入操作
  const handleBatchImportTopics = () => {
    const titles: string[] = [];
    selectedNodeIds.forEach((id) => {
      const title = nodeTitleMap.get(id);
      if (title && !existingTopics.includes(title)) {
        titles.push(title);
      }
    });
    if (titles.length > 0) {
      onAddTopics(titles);
    }
    setSelectedNodeIds(new Set());
  };

  const handleBatchImportExcluded = () => {
    const titles: string[] = [];
    selectedNodeIds.forEach((id) => {
      const title = nodeTitleMap.get(id);
      if (title && !existingExcluded.includes(title)) {
        titles.push(title);
      }
    });
    if (titles.length > 0) {
      onAddExcludedTopics(titles);
    }
    setSelectedNodeIds(new Set());
  };

  // 统计章节和课时
  const stats = useMemo(() => {
    let totalChapters = 0;
    let totalLessons = 0;
    const countNodes = (nodes: ChapterTreeNode[], depth = 0) => {
      nodes.forEach((n) => {
        if (depth === 0) totalChapters++;
        else totalLessons++;
        if (n.child_nodes && n.child_nodes.length > 0) {
          countNodes(n.child_nodes, depth + 1);
        }
      });
    };
    countNodes(chapters);
    return { totalChapters, totalLessons };
  }, [chapters]);

  // 过滤后的章节树
  const filteredChapters = useMemo(() => {
    if (!filterKw.trim()) return chapters;
    const kw = filterKw.trim().toLowerCase();

    const filterNode = (node: ChapterTreeNode): ChapterTreeNode | null => {
      const matchSelf = node.title?.toLowerCase().includes(kw);
      let matchedChildren: ChapterTreeNode[] = [];

      if (node.child_nodes && node.child_nodes.length > 0) {
        matchedChildren = node.child_nodes
          .map((c) => filterNode(c))
          .filter((c): c is ChapterTreeNode => c !== null);
      }

      if (matchSelf || matchedChildren.length > 0) {
        return {
          ...node,
          child_nodes: matchedChildren.length > 0 ? matchedChildren : node.child_nodes,
        };
      }
      return null;
    };

    return chapters.map((c) => filterNode(c)).filter((c): c is ChapterTreeNode => c !== null);
  }, [chapters, filterKw]);

  // 单独渲染树节点
  const renderTreeNode = (node: ChapterTreeNode, depth = 0) => {
    const hasChildren = Boolean(node.child_nodes && node.child_nodes.length > 0);
    const isExpanded = expandedNodeIds.has(node.id);
    const isSelected = selectedNodeIds.has(node.id);
    const isInTopics = existingTopics.includes(node.title);
    const isInExcluded = existingExcluded.includes(node.title);

    return (
      <div key={node.id} className="select-none">
        <div
          className={`group flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-slate-100/80 transition text-xs ${
            isSelected ? 'bg-brand-50/70 text-brand-900 font-semibold' : 'text-slate-700'
          }`}
          style={{ paddingLeft: `${depth * 18 + 8}px` }}
        >
          <div className="flex items-center gap-1.5 flex-1 min-w-0 pr-2">
            {/* 折叠开关 */}
            {hasChildren ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  toggleExpand(node.id);
                }}
                className="w-4 h-4 flex items-center justify-center text-slate-400 hover:text-slate-700 shrink-0"
              >
                {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
              </button>
            ) : (
              <span className="w-4 h-4 shrink-0" />
            )}

            {/* 勾选框 */}
            <button
              type="button"
              onClick={() => toggleSelectNode(node)}
              className="text-slate-400 hover:text-brand-600 transition shrink-0"
            >
              {isSelected ? (
                <CheckSquare className="w-3.5 h-3.5 text-brand-600" />
              ) : (
                <Square className="w-3.5 h-3.5" />
              )}
            </button>

            {/* 节点图标 */}
            {depth === 0 ? (
              isExpanded ? (
                <FolderOpen className="w-3.5 h-3.5 text-amber-500 shrink-0" />
              ) : (
                <Folder className="w-3.5 h-3.5 text-amber-500 shrink-0" />
              )
            ) : (
              <FileText className="w-3 h-3 text-slate-400 shrink-0" />
            )}

            {/* 标题 */}
            <span
              onClick={() => toggleSelectNode(node)}
              className={`truncate cursor-pointer ${
                depth === 0 ? 'font-bold text-slate-900' : depth === 1 ? 'font-medium' : 'text-slate-600'
              }`}
            >
              {node.title}
            </span>

            {/* 已加入状态标记 */}
            {isInTopics && (
              <span className="px-1.5 py-0.2 rounded-sm bg-emerald-100 text-emerald-800 text-[10px] font-bold shrink-0">
                已考查
              </span>
            )}
            {isInExcluded && (
              <span className="px-1.5 py-0.2 rounded-sm bg-rose-100 text-rose-800 text-[10px] font-bold shrink-0">
                已排除
              </span>
            )}
          </div>

          {/* 快捷悬浮操作按钮 */}
          <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1 shrink-0 transition">
            {!isInTopics && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onAddTopics([node.title]);
                }}
                className="px-1.5 py-0.5 rounded-sm bg-emerald-50 hover:bg-emerald-600 text-emerald-700 hover:text-white text-[10px] font-semibold border border-emerald-200 transition"
              >
                + 考查
              </button>
            )}
            {!isInExcluded && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onAddExcludedTopics([node.title]);
                }}
                className="px-1.5 py-0.5 rounded-sm bg-rose-50 hover:bg-rose-600 text-rose-700 hover:text-white text-[10px] font-semibold border border-rose-200 transition"
              >
                + 排除
              </button>
            )}
          </div>
        </div>

        {/* 子节点递归 */}
        {hasChildren && isExpanded && (
          <div className="space-y-0.5">
            {node.child_nodes!.map((child) => renderTreeNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="border border-slate-200 rounded-2xl bg-white p-4 shadow-xs space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 flex-wrap border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-brand-600" />
          <h3 className="text-xs font-bold text-slate-900">
            官方章节目录树 (划定命题考查与排除范围)
          </h3>
          {textbookTitle && (
            <span className="px-2 py-0.5 bg-brand-50 text-brand-700 font-semibold rounded-full text-[11px] truncate max-w-xs">
              {textbookTitle}
            </span>
          )}
        </div>

        {chapters.length > 0 && (
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span>
              共 <strong className="text-slate-900">{stats.totalChapters}</strong> 章，
              <strong className="text-brand-600">{stats.totalLessons}</strong> 小节
            </span>
            <div className="flex items-center gap-1 border-l border-slate-200 pl-2">
              <button
                type="button"
                onClick={expandAll}
                className="hover:text-slate-900 transition px-1 py-0.5 rounded hover:bg-slate-100 text-[11px]"
              >
                展开全部
              </button>
              <span>·</span>
              <button
                type="button"
                onClick={collapseAll}
                className="hover:text-slate-900 transition px-1 py-0.5 rounded hover:bg-slate-100 text-[11px]"
              >
                折叠全部
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Chapter Search & Batch Action Bar */}
      {chapters.length > 0 && (
        <div className="flex items-center justify-between gap-3 flex-wrap">
          {/* Quick Search in chapters */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" />
            <input
              type="text"
              value={filterKw}
              onChange={(e) => setFilterKw(e.target.value)}
              placeholder="搜索章节、课时名称..."
              className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
            />
          </div>

          {/* Batch Actions */}
          <div className="flex items-center gap-2">
            {selectedNodeIds.size > 0 && (
              <span className="text-xs font-semibold text-slate-600">
                已勾选 <strong className="text-brand-600">{selectedNodeIds.size}</strong> 项
              </span>
            )}
            <button
              type="button"
              onClick={handleBatchImportTopics}
              disabled={selectedNodeIds.size === 0}
              className="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-200 text-white font-bold text-xs rounded-lg transition shadow-xs flex items-center gap-1"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>导入为考查范围</span>
            </button>
            <button
              type="button"
              onClick={handleBatchImportExcluded}
              disabled={selectedNodeIds.size === 0}
              className="px-2.5 py-1.5 bg-rose-600 hover:bg-rose-700 disabled:bg-slate-200 text-white font-bold text-xs rounded-lg transition shadow-xs flex items-center gap-1"
            >
              <Ban className="w-3.5 h-3.5" />
              <span>设为超纲排除</span>
            </button>
            {selectedNodeIds.size > 0 && (
              <button
                type="button"
                onClick={() => setSelectedNodeIds(new Set())}
                className="text-slate-400 hover:text-slate-600 text-xs px-1"
              >
                清空
              </button>
            )}
          </div>
        </div>
      )}

      {/* Tree Content Container */}
      <div className="border border-slate-200 rounded-xl max-h-72 overflow-y-auto p-2 bg-slate-50/50">
        {isLoading ? (
          <div className="p-8 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
            <Sparkles className="w-4 h-4 animate-spin text-brand-600" />
            <span>正在从智慧教育平台加载官方章节目录...</span>
          </div>
        ) : !materialId ? (
          <div className="p-8 text-center text-slate-400 text-xs">
            👈 请先在上方【1. 基础信息】中选用具体教材，系统将即刻呈现该书完整大纲目录。
          </div>
        ) : filteredChapters.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-xs">
            {filterKw ? '未搜索到匹配章节' : '该教材暂无结构化章节目录'}
          </div>
        ) : (
          <div className="space-y-0.5">
            {filteredChapters.map((ch) => renderTreeNode(ch, 0))}
          </div>
        )}
      </div>

      <div className="text-[11px] text-slate-500 flex items-center justify-between">
        <span>💡 支持在左侧勾选后批量导入，或鼠标悬停单节点击“+ 考查”快速添加。</span>
        <span className="text-slate-400 font-mono">Trees Source: basic.smartedu.cn</span>
      </div>
    </div>
  );
};
