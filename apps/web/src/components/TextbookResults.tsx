import React from 'react';
import { Check } from 'lucide-react';
import { TextbookSummary } from '../types/spec';

interface TextbookResultsProps {
  isLoading: boolean;
  materials: TextbookSummary[];
  currentMaterialId?: string;
  onSelect: (material: TextbookSummary) => void;
  onClose: () => void;
}

export const TextbookResults: React.FC<TextbookResultsProps> = ({ isLoading, materials, currentMaterialId, onSelect, onClose }) => (
  <div className="border-t border-slate-200 pt-5">
    <div className="text-xs font-bold text-slate-600 uppercase tracking-wider mb-3">
      当前维度匹配结果 (共 {materials.length} 本教材)
    </div>
    {isLoading ? (
      <div className="p-8 text-center text-slate-500 text-sm">正在加载教材库...</div>
    ) : materials.length === 0 ? (
      <div className="p-8 text-center text-slate-400 border border-dashed border-slate-300 rounded-xl text-sm">
        当前组合暂无对应教材，可切换为【全库全部】模式或调整筛选条件。
      </div>
    ) : (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {materials.map((material) => {
          const selected = material.id === currentMaterialId;
          const isNew = material.title.includes('新教材');
          const thumbSrc = material.thumb || `http://localhost:8000/v1/curriculum/covers/${material.id}.jpg`;
          return (
            <div key={material.id} className={`p-4 rounded-xl border transition flex gap-3.5 items-start ${selected ? 'border-brand-600 bg-brand-50/50 ring-2 ring-brand-500/20' : 'border-slate-200 hover:border-slate-300 bg-white shadow-xs'}`}>
              <img src={thumbSrc} alt="cover" referrerPolicy="no-referrer" className="w-16 h-22 object-cover rounded-md border border-slate-200 shrink-0 shadow-xs bg-slate-100" onError={(event) => { (event.target as HTMLElement).style.display = 'none'; }} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 flex-wrap mb-1">
                  {isNew ? <span className="px-1.5 py-0.5 rounded-sm bg-emerald-100 text-emerald-800 font-bold text-[10px]">新教材</span> : <span className="px-1.5 py-0.5 rounded-sm bg-slate-100 text-slate-600 font-medium text-[10px]">原版/旧版</span>}
                  {material.isVisible ? (
                    <span className="px-1.5 py-0.5 rounded-sm bg-emerald-50 text-emerald-700 font-semibold text-[10px] border border-emerald-200">🟢 官网开放</span>
                  ) : (
                    <span title={material.visReason} className="px-1.5 py-0.5 rounded-sm bg-amber-50 text-amber-800 font-semibold text-[10px] border border-amber-200 flex items-center gap-0.5">🔒 官网隐藏</span>
                  )}
                  {material.hasVocab && <span className="px-1.5 py-0.5 rounded-sm bg-sky-100 text-sky-800 font-bold text-[10px]">📖 含词表 ({material.vocabCount}页)</span>}
                </div>
                <div className="font-bold text-sm text-slate-900 leading-snug line-clamp-2">{material.title}</div>
                <div className="text-[11px] font-mono text-slate-400 mt-1 truncate">ID: {material.id}</div>
                {!material.isVisible && <div className="text-[10px] text-amber-700 mt-1.5 bg-amber-50 p-1 rounded-sm border border-amber-100">原因: {material.visReason}</div>}
                <div className="mt-3">
                  <button type="button" onClick={() => { onSelect(material); onClose(); }} className="px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-lg transition shadow-xs flex items-center gap-1.5">
                    <Check className="w-3.5 h-3.5" /><span>确认选用此教材</span>
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    )}
  </div>
);
