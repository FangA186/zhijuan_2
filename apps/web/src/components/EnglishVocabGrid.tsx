import React from 'react';
import { BookOpen, Eye, RotateCcw, Upload, X } from 'lucide-react';
import { TextbookVocabData, TextbookVocabImage } from '../types/spec';
import { api } from '../lib/api';

interface EnglishVocabGridProps {
  images: TextbookVocabImage[];
  vocabData: TextbookVocabData | null;
  isUploading: boolean;
  onPreview: (index: number) => void;
  onRemove: (index: number, event: React.MouseEvent) => void;
  onUpload: () => void;
  onReset: () => void;
}

export const EnglishVocabGrid: React.FC<EnglishVocabGridProps> = ({ images, vocabData, isUploading, onPreview, onRemove, onUpload, onReset }) => images.length ? (
  <div className="space-y-1.5">
    <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 pt-1">
      {images.map((image, index) => (
        <div key={image.filename + index} onClick={() => onPreview(index)} className="group relative rounded-xl border border-slate-200 overflow-hidden bg-slate-50 hover:border-brand-500 hover:shadow-md transition-all cursor-pointer aspect-3/4 flex flex-col items-center justify-between p-1.5">
          <img src={api.getVocabImageUrl(vocabData?.material_id || '', image.filename, image.url)} alt={`Page ${image.page_num}`} loading="lazy" className="w-full h-full object-cover rounded-lg group-hover:scale-105 transition-transform duration-200" />
          <div className="absolute inset-0 bg-slate-900/0 group-hover:bg-slate-900/25 transition-all rounded-xl flex items-center justify-center"><Eye className="w-5 h-5 text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-md" /></div>
          <button type="button" onClick={(event) => onRemove(index, event)} title="从本次考查词表中移除此页" className="absolute top-1.5 right-1.5 w-6 h-6 rounded-full bg-slate-900/70 hover:bg-rose-600 text-white flex items-center justify-center transition-all opacity-0 group-hover:opacity-100 shadow-md cursor-pointer z-10"><X className="w-3.5 h-3.5" /></button>
          <div className="absolute bottom-1.5 left-1.5 px-1.5 py-0.5 rounded bg-slate-900/75 backdrop-blur-xs text-[10px] font-mono font-medium text-white shadow-xs flex items-center gap-1"><span>P.{image.page_num}</span>{image.filename.startsWith('custom_') && <span className="text-[9px] text-amber-300 font-sans font-normal">自定义</span>}</div>
        </div>
      ))}
    </div>
    <div className="text-[11px] text-slate-400 text-right pt-0.5">点击图片进入全屏画廊浏览 · 悬停可点击右上角 ✕ 移除页面</div>
  </div>
) : (
  <div className="p-8 border-2 border-dashed border-slate-200 rounded-2xl flex flex-col items-center justify-center text-center space-y-3 bg-slate-50/50 my-1">
    <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center text-slate-400"><BookOpen className="w-6 h-6" /></div>
    <div className="space-y-1"><div className="text-sm font-bold text-slate-700">暂无选定的教材词表页面</div><div className="text-xs text-slate-500 max-w-md">{vocabData && vocabData.images.length > 0 ? '您已移除了该教材的所有词表页面。可随时恢复原版默认，或上传自定义词表图片。' : '当前教材暂未收录官方原版词表。您可以点击下方按钮上传校本讲义、单元词汇表或自编核心单词图片。'}</div></div>
    <div className="flex items-center gap-3 pt-2">
      <button type="button" onClick={onUpload} disabled={isUploading} className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs rounded-xl shadow-xs transition flex items-center gap-2 cursor-pointer disabled:opacity-50"><Upload className="w-4 h-4" /><span>{isUploading ? '正在上传...' : '上传词表图片 (支持JPG/PNG/WEBP)'}</span></button>
      {vocabData && vocabData.images.length > 0 && <button type="button" onClick={onReset} className="px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 font-semibold text-xs rounded-xl transition flex items-center gap-1.5 cursor-pointer"><RotateCcw className="w-3.5 h-3.5" /><span>恢复原版默认 ({vocabData.image_count}页)</span></button>}
    </div>
  </div>
);
