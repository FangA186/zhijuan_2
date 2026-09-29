import { useEffect, useMemo, useState } from 'react';
import { ChapterTreeNode } from '../types/spec';
import { api } from '../lib/api';
import { collectChapterNodeIds, collectChapterTitles, filterChapterTree, getChapterStats, getDescendantTitles, initializeChapterTree, nonQuestionableTitles } from './chapterTreeUtils';

export interface ChapterTreeScopeSelectorProps {
  materialId?: string;
  textbookTitle?: string;
  onAddTopics: (topics: string[]) => void;
  onRemoveTopic?: (topic: string) => void;
  onRemoveTopics?: (topics: string[]) => void;
  onClearAllTopics?: () => void;
  onAddExcludedTopics?: (topics: string[]) => void;
  existingTopics: string[];
  existingExcluded?: string[];
}

export const useChapterTreeScope = ({ materialId, onAddTopics, onRemoveTopic, onRemoveTopics, onClearAllTopics, onAddExcludedTopics, existingTopics, existingExcluded = [] }: ChapterTreeScopeSelectorProps) => {
  const [chapters, setChapters] = useState<ChapterTreeNode[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedNodeIds, setExpandedNodeIds] = useState<Set<string>>(new Set());
  const [selectedNodeIds, setSelectedNodeIds] = useState<Set<string>>(new Set());
  const [filterKw, setFilterKw] = useState('');
  const [nonQuestionableNotice, setNonQuestionableNotice] = useState('');
  const [nodeTitleMap, setNodeTitleMap] = useState<Map<string, string>>(new Map());

  useEffect(() => {
    if (!materialId) { setChapters([]); return; }
    void loadChapterTree(materialId);
  }, [materialId]);

  const loadChapterTree = async (id: string) => {
    setIsLoading(true);
    try {
      const response = await api.getMaterialChapterTree(id);
      if (!response?.chapters) { setChapters([]); return; }
      setChapters(response.chapters);
      const initial = initializeChapterTree(response.chapters);
      setExpandedNodeIds(initial.expandedNodeIds);
      setNodeTitleMap(initial.nodeTitleMap);
      setSelectedNodeIds(new Set());
    } catch (error) {
      console.error(error);
      setChapters([]);
    } finally { setIsLoading(false); }
  };

  const toggleExpand = (nodeId: string) => setExpandedNodeIds((prev) => {
    const next = new Set(prev);
    if (next.has(nodeId)) next.delete(nodeId); else next.add(nodeId);
    return next;
  });
  const expandAll = () => setExpandedNodeIds(new Set(collectChapterNodeIds(chapters)));
  const collapseAll = () => setExpandedNodeIds(new Set());

  const toggleSelectNode = (node: ChapterTreeNode) => {
    const familyTitles = getDescendantTitles(node);
    const allSelected = familyTitles.length > 0 && familyTitles.every((title) => existingTopics.includes(title));
    if (onRemoveTopics || onRemoveTopic) {
      if (existingTopics.includes(node.title) || allSelected) {
        if (onRemoveTopics) onRemoveTopics(familyTitles);
        else familyTitles.forEach((title) => onRemoveTopic?.(title));
      } else {
        onAddTopics(familyTitles);
        const invalid = nonQuestionableTitles(familyTitles);
        if (invalid.length) setNonQuestionableNotice(`所选范围包含「${invalid.join('、')}」等结构项，不确定都能直接出题，请教师逐项核对后在下方确认考查范围。`);
      }
      return;
    }
    setSelectedNodeIds((prev) => {
      const next = new Set(prev);
      const select = !next.has(node.id);
      const visit = (current: ChapterTreeNode) => { if (select) next.add(current.id); else next.delete(current.id); current.child_nodes?.forEach(visit); };
      visit(node);
      return next;
    });
  };

  const handleSelectAllChapters = () => {
    const titles = collectChapterTitles(chapters);
    if (!titles.length) return;
    onAddTopics(titles);
    const invalid = nonQuestionableTitles(titles);
    setNonQuestionableNotice(invalid.length ? `全卷范围包含章节标题、正文小节与「${invalid.join('、')}」等结构项。这些项不一定能直接出题（例如复习、小结、阅读板块），系统不按标题自动保证可用；请教师逐项核对并仅保留适合直接命题的知识点，再勾选「我已确认本次考查范围」。` : '');
  };
  const handleClearAllSelected = () => {
    if (onClearAllTopics) onClearAllTopics();
    else if (onRemoveTopics) onRemoveTopics(existingTopics);
    else existingTopics.forEach((title) => onRemoveTopic?.(title));
    setSelectedNodeIds(new Set());
    setNonQuestionableNotice('');
  };
  const getBatchTitles = (exclude = false) => Array.from(selectedNodeIds).flatMap((id) => {
    const title = nodeTitleMap.get(id);
    const existing = exclude ? existingExcluded : existingTopics;
    return title && !existing.includes(title) ? [title] : [];
  });
  const handleBatchImportTopics = () => { const titles = getBatchTitles(); if (titles.length) onAddTopics(titles); setSelectedNodeIds(new Set()); };
  const handleBatchImportExcluded = () => { const titles = getBatchTitles(true); if (titles.length) onAddExcludedTopics?.(titles); setSelectedNodeIds(new Set()); };
  const stats = useMemo(() => getChapterStats(chapters), [chapters]);
  const filteredChapters = useMemo(() => filterChapterTree(chapters, filterKw), [chapters, filterKw]);

  return { chapters, isLoading, expandedNodeIds, selectedNodeIds, filterKw, setFilterKw, nonQuestionableNotice, existingTopics, existingExcluded, onRemoveTopic, onAddExcludedTopics, stats, filteredChapters, toggleExpand, expandAll, collapseAll, toggleSelectNode, handleSelectAllChapters, handleClearAllSelected, handleBatchImportTopics, handleBatchImportExcluded };
};
