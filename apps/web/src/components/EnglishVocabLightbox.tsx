import React from 'react';
import { ChevronLeft, ChevronRight, Trash2, X } from 'lucide-react';
import { TextbookVocabData, TextbookVocabImage } from '../types/spec';
import { api } from '../lib/api';

interface EnglishVocabLightboxProps {
  previewIndex: number | null;
  images: TextbookVocabImage[];
  vocabData: TextbookVocabData | null;
  setPreviewIndex: (index: number | null) => void;
  onRemove: (index: number, event: React.MouseEvent) => void;
}

export const EnglishVocabLightbox: React.FC<EnglishVocabLightboxProps> = ({ previewIndex, images, vocabData, setPreviewIndex, onRemove }) => {
  if (previewIndex === null || !images[previewIndex]) return null;
  const current = images[previewIndex];
  return (
    <div className="fixed inset-0 z-50 bg-slate-950/85 backdrop-blur-sm flex flex-col items-center justify-between p-4 sm:p-6" onClick={() => setPreviewIndex(null)}>
      <div className="w-full max-w-5xl flex items-center justify-between text-white py-1" onClick={(event) => event.stopPropagation()}>
        <div className="flex items-center gap-2.5 flex-wrap">
          <span className="font-bold text-sm sm:text-base tracking-tight">{vocabData?.title || '词汇表预览'}</span>
          <span className="px-2.5 py-0.5 rounded-full bg-white/20 text-xs font-mono font-medium">第 {previewIndex + 1} / {images.length} 页 (P.{current.page_num})</span>
          {current.filename.startsWith('custom_') ? <span className="px-2 py-0.5 rounded-full bg-amber-500/20 border border-amber-400/40 text-amber-300 text-[11px] font-semibold">自选手传</span> : <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 text-[11px] font-semibold">官方原版</span>}
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={(event) => onRemove(previewIndex, event)} className="px-3 py-1.5 rounded-xl bg-rose-600/80 hover:bg-rose-600 text-white text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer" title="从本次考查词表中移除"><Trash2 className="w-3.5 h-3.5" /><span>移除此页</span></button>
          <button type="button" onClick={() => setPreviewIndex(null)} className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white transition cursor-pointer" title="关闭画廊"><X className="w-5 h-5" /></button>
        </div>
      </div>
      <div className="relative flex-1 w-full max-w-5xl flex items-center justify-center my-2" onClick={(event) => event.stopPropagation()}>
        {previewIndex > 0 && <button type="button" onClick={() => setPreviewIndex(previewIndex - 1)} className="absolute left-2 sm:left-4 z-10 p-3 rounded-full bg-black/60 hover:bg-black/80 text-white transition cursor-pointer shadow-xl" title="上一页"><ChevronLeft className="w-6 h-6" /></button>}
        <img src={api.getVocabImageUrl(vocabData?.material_id || '', current.filename, current.url)} alt={`Page ${current.page_num}`} className="max-h-[76vh] max-w-full object-contain rounded-xl shadow-2xl border border-white/10" />
        {previewIndex < images.length - 1 && <button type="button" onClick={() => setPreviewIndex(previewIndex + 1)} className="absolute right-2 sm:right-4 z-10 p-3 rounded-full bg-black/60 hover:bg-black/80 text-white transition cursor-pointer shadow-xl" title="下一页"><ChevronRight className="w-6 h-6" /></button>}
      </div>
      <div className="flex items-center gap-2 overflow-x-auto max-w-2xl py-1 px-3 bg-white/5 rounded-2xl border border-white/10 backdrop-blur-xs" onClick={(event) => event.stopPropagation()}>
        {images.map((image, index) => <button key={image.filename + index} type="button" onClick={() => setPreviewIndex(index)} className={`shrink-0 w-11 h-14 rounded-md overflow-hidden border-2 transition cursor-pointer relative ${previewIndex === index ? 'border-brand-400 scale-105 shadow-md ring-2 ring-brand-400/30' : 'border-white/20 opacity-60 hover:opacity-100'}`}><img src={api.getVocabImageUrl(vocabData?.material_id || '', image.filename, image.url)} alt={`thumb ${image.page_num}`} className="w-full h-full object-cover" /><span className="absolute bottom-0 right-0 px-1 py-0.2 rounded-tl bg-black/80 text-[8px] font-mono text-white">{image.page_num}</span></button>)}
      </div>
    </div>
  );
};
