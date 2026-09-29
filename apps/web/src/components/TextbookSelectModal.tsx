import React, { useState } from 'react';
import { X, BookOpen } from 'lucide-react';
import { TextbookSummary, Stage } from '../types/spec';
import { useTextbookCatalog } from './useTextbookCatalog';
import { TextbookCascadeSelectors } from './TextbookCascadeSelectors';
import { TextbookResults } from './TextbookResults';
import { TextbookSelectTabs } from './TextbookSelectTabs';
import { TextbookSearchPanel } from './TextbookSearchPanel';
import { TextbookUrlPanel } from './TextbookUrlPanel';
import { useTextbookSearch } from './useTextbookSearch';
import { useTextbookUrlImport } from './useTextbookUrlImport';
import { TextbookFilterMode, TextbookSelectTab } from './textbookSelectionTypes';

interface TextbookSelectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (material: TextbookSummary) => void;
  currentMaterialId?: string;
  initialStage?: Stage;
}

export const TextbookSelectModal: React.FC<TextbookSelectModalProps> = ({ isOpen, onClose, onSelect, currentMaterialId, initialStage = 'junior' }) => {
  const [activeTab, setActiveTab] = useState<TextbookSelectTab>('cascade');
  const [filterMode, setFilterMode] = useState<TextbookFilterMode>('visible');
  const catalog = useTextbookCatalog(isOpen, currentMaterialId, initialStage, filterMode);
  const search = useTextbookSearch(catalog.allMaterials);
  const urlImport = useTextbookUrlImport(catalog.allMaterials);
  const choose = (material: TextbookSummary) => { onSelect(material); onClose(); };
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white w-full max-w-4xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-150">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-brand-100 text-brand-700 flex items-center justify-center font-bold"><BookOpen className="w-5 h-5" /></div>
            <div>
              <div className="text-base font-bold text-slate-900 flex items-center gap-2"><span>选择国家标准教材 (国家中小学智慧教育平台)</span><span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">{filterMode === 'visible' ? '官网开放 1727 本' : '全库 3209 本'}</span></div>
              <div className="text-xs text-slate-500">严格遵循国家课程标准与智慧教育平台导航体系，选定教材后将自动同步试卷规格并加载章节目录树</div>
            </div>
          </div>
          <button type="button" onClick={onClose} className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"><X className="w-5 h-5" /></button>
        </div>
        <TextbookSelectTabs activeTab={activeTab} onTabChange={setActiveTab} filterMode={filterMode} onFilterModeChange={setFilterMode} />
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {activeTab === 'cascade' && <>
            <TextbookCascadeSelectors hasGrade={catalog.hasGrade} stageOptions={catalog.stageOptions} gradeOptions={catalog.gradeOptions} subjectOptions={catalog.subjectOptions} editionOptions={catalog.editionOptions} termOptions={catalog.termOptions} selectedXd={catalog.selectedXd} selectedNj={catalog.selectedNj} selectedXk={catalog.selectedXk} selectedBb={catalog.selectedBb} selectedCc={catalog.selectedCc} setSelectedXd={catalog.setSelectedXd} setSelectedNj={catalog.setSelectedNj} setSelectedXk={catalog.setSelectedXk} setSelectedBb={catalog.setSelectedBb} setSelectedCc={catalog.setSelectedCc} />
            <TextbookResults isLoading={catalog.isLoading} materials={catalog.matchedMaterials} currentMaterialId={currentMaterialId} onSelect={onSelect} onClose={onClose} />
          </>}
          {activeTab === 'search' && <TextbookSearchPanel searchKw={search.searchKw} results={search.searchResults} onSearch={search.handleSearch} onChoose={choose} />}
          {activeTab === 'url' && <TextbookUrlPanel urlInput={urlImport.urlInput} urlError={urlImport.urlError} matchedMaterial={urlImport.urlMatchedMat} onInputChange={urlImport.setUrlInput} onParse={urlImport.handleParseUrl} onChoose={choose} />}
        </div>
        <div className="px-6 py-3 border-t border-slate-200 bg-slate-50/50 flex items-center justify-between text-xs text-slate-500"><div>💡 选择教材后，知卷将自动解析教材体系并加载其全册官方章节目录树。</div><button type="button" onClick={onClose} className="px-4 py-1.5 border border-slate-300 hover:bg-slate-100 rounded-lg text-slate-700 font-semibold transition">关闭</button></div>
      </div>
    </div>
  );
};
