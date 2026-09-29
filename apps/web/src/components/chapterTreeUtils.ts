import { ChapterTreeNode } from '../types/spec';

const NON_QUESTIONABLE_HINTS = ['阅读与思考', '阅读与鉴赏', '复习', '小结', '本章小结', '数学活动', '活动与探究', '实验', '课题'];

export const getDescendantTitles = (node: ChapterTreeNode): string[] => {
  const titles: string[] = [];
  const visit = (current: ChapterTreeNode) => {
    if (current.title) titles.push(current.title);
    current.child_nodes?.forEach(visit);
  };
  visit(node);
  return titles;
};

export const collectChapterTitles = (nodes: ChapterTreeNode[]): string[] => nodes.flatMap(getDescendantTitles);
export const nonQuestionableTitles = (titles: string[]) => titles.filter((title) => NON_QUESTIONABLE_HINTS.some((hint) => title.includes(hint)));

export const getChapterStats = (chapters: ChapterTreeNode[]) => {
  let totalChapters = 0;
  let totalLessons = 0;
  const visit = (nodes: ChapterTreeNode[], depth = 0) => nodes.forEach((node) => {
    if (depth === 0) totalChapters++;
    else totalLessons++;
    if (node.child_nodes?.length) visit(node.child_nodes, depth + 1);
  });
  visit(chapters);
  return { totalChapters, totalLessons };
};

export const filterChapterTree = (chapters: ChapterTreeNode[], keyword: string): ChapterTreeNode[] => {
  if (!keyword.trim()) return chapters;
  const query = keyword.trim().toLowerCase();
  const filterNode = (node: ChapterTreeNode): ChapterTreeNode | null => {
    const matchesSelf = node.title?.toLowerCase().includes(query);
    const children = node.child_nodes?.map(filterNode).filter((child): child is ChapterTreeNode => child !== null) || [];
    return matchesSelf || children.length ? { ...node, child_nodes: children.length ? children : node.child_nodes } : null;
  };
  return chapters.map(filterNode).filter((node): node is ChapterTreeNode => node !== null);
};

export const initializeChapterTree = (chapters: ChapterTreeNode[]) => {
  const expandedNodeIds = new Set<string>();
  const nodeTitleMap = new Map<string, string>();
  const visit = (nodes: ChapterTreeNode[], depth = 0) => nodes.forEach((node, index) => {
    if (depth < 1 || index < 2) expandedNodeIds.add(node.id);
    if (node.title) nodeTitleMap.set(node.id, node.title);
    if (node.child_nodes?.length) visit(node.child_nodes, depth + 1);
  });
  visit(chapters);
  return { expandedNodeIds, nodeTitleMap };
};

export const collectChapterNodeIds = (nodes: ChapterTreeNode[]): string[] => nodes.flatMap((node) => [node.id, ...collectChapterNodeIds(node.child_nodes || [])]);
