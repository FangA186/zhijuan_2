import React from 'react';
import { ChapterTreePanel } from './ChapterTreePanel';
import { ChapterTreeScopeSelectorProps, useChapterTreeScope } from './useChapterTreeScope';

export type { ChapterTreeScopeSelectorProps } from './useChapterTreeScope';

export const ChapterTreeScopeSelector: React.FC<ChapterTreeScopeSelectorProps> = (props) => {
  const tree = useChapterTreeScope(props);
  return <ChapterTreePanel materialId={props.materialId} textbookTitle={props.textbookTitle} chapters={tree.chapters} filteredChapters={tree.filteredChapters} isLoading={tree.isLoading} filterKw={tree.filterKw} setFilterKw={tree.setFilterKw} stats={tree.stats} expandedNodeIds={tree.expandedNodeIds} selectedNodeIds={tree.selectedNodeIds} existingTopics={tree.existingTopics} existingExcluded={tree.existingExcluded} externalSelection={Boolean(tree.onRemoveTopic)} nonQuestionableNotice={tree.nonQuestionableNotice} onToggleSelect={tree.toggleSelectNode} onToggleExpand={tree.toggleExpand} onExpandAll={tree.expandAll} onCollapseAll={tree.collapseAll} onSelectAll={tree.handleSelectAllChapters} onClearAll={tree.handleClearAllSelected} onBatchImportTopics={tree.handleBatchImportTopics} onBatchImportExcluded={tree.handleBatchImportExcluded} hasExcludedHandler={Boolean(tree.onAddExcludedTopics)} />;
};
