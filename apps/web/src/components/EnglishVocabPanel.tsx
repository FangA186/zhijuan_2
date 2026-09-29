import React from 'react';
import { BookOpen, Plus, RotateCcw, Sparkles, X } from 'lucide-react';
import { TextbookVocabData } from '../types/spec';

interface EnglishVocabPanelProps {
  vocabData: TextbookVocabData | null;
  isLoading: boolean;
  isCustomized: boolean;
  imageCount: number;
  isUploading: boolean;
  uploadError: string | null;
  onUpload: () => void;
  onReset: () => void;
  onClearError: () => void;
  children: React.ReactNode;
}

export const EnglishVocabPanel: React.FC<EnglishVocabPanelProps> = ({ vocabData, isLoading, isCustomized, imageCount, isUploading, uploadError, onUpload, onReset, onClearError, children }) => {
  if (isLoading) return <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex items-center gap-2 text-xs text-slate-500"><Sparkles className="w-4 h-4 text-brand-500 animate-spin" /><span>正在匹配教材词表与高清图片索引...</span></div>;
  return (
    <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs space-y-3.5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs shrink-0"><BookOpen className="w-4 h-4" /></div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <div className="text-sm font-bold text-slate-900">{isCustomized ? '考查词汇表 (已自定义)' : '原版教材词汇表'}</div>
              <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-[11px] font-semibold">已选定 {imageCount} 页图片</span>
              {isCustomized && <span className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 text-[11px] font-semibold">自定义模式</span>}
              {!isCustomized && vocabData?.start_page && <span className="text-xs text-slate-400">(第 {vocabData.start_page} ~ {vocabData.end_page} 页)</span>}
            </div>
            <div className="text-xs text-slate-500 mt-0.5">{isCustomized ? '已根据本次考试要求定制词表范围（支持继续补充上传或移除不考页面）' : (vocabData?.summary || '经知卷清洗入库的官方原版词汇表，支持在线画廊预览与自主自定义')}</div>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
          <button type="button" onClick={onUpload} disabled={isUploading} className="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-300 font-semibold text-xs rounded-xl transition flex items-center gap-1.5 cursor-pointer disabled:opacity-50"><Plus className="w-3.5 h-3.5" /><span>{isUploading ? '上传中...' : '上传/补充图片'}</span></button>
          {isCustomized && <button type="button" onClick={onReset} className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-300 font-semibold text-xs rounded-xl transition flex items-center gap-1.5 cursor-pointer" title="恢复为教材原始官方词表"><RotateCcw className="w-3.5 h-3.5" /><span>恢复原版默认</span></button>}
        </div>
      </div>
      {uploadError && <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center justify-between"><span>{uploadError}</span><button type="button" onClick={onClearError} className="text-rose-500 hover:text-rose-800 cursor-pointer"><X className="w-3.5 h-3.5" /></button></div>}
      {children}
    </div>
  );
};
