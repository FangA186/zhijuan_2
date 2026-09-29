import React from 'react';
import { X, Upload, Layers, Download, FileUp } from 'lucide-react';

export type ExamTemplateTab = 'upload' | 'preset';
interface ExamTemplateDialogProps {
  activeTab: ExamTemplateTab;
  setActiveTab: (tab: ExamTemplateTab) => void;
  onClose: () => void;
  onDownloadSample: () => void;
  children: React.ReactNode;
}

export const ExamTemplateDialog: React.FC<ExamTemplateDialogProps> = ({ activeTab, setActiveTab, onClose, onDownloadSample, children }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
    <div className="bg-white w-full max-w-2xl rounded-3xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-150">
      <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50"><div className="flex items-center gap-3"><div className="w-10 h-10 rounded-2xl bg-brand-100 text-brand-700 flex items-center justify-center font-bold"><FileUp className="w-5 h-5" /></div><div><div className="text-base font-bold text-slate-900 flex items-center gap-2"><span>试卷模板与参考示例</span></div><div className="text-xs text-slate-500 mt-0.5">可上传已有试卷自动识别题型结构，或直接选用国家标准精品示例</div></div></div><button type="button" onClick={onClose} className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition cursor-pointer"><X className="w-5 h-5" /></button></div>
      <div className="px-6 pt-3 border-b border-slate-200 flex items-center justify-between bg-white"><div className="flex gap-4">{(['upload', 'preset'] as const).map((tab) => <button key={tab} type="button" onClick={() => setActiveTab(tab)} className={`pb-3 text-xs font-bold transition border-b-2 cursor-pointer flex items-center gap-1.5 ${activeTab === tab ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-800'}`}>{tab === 'upload' ? <><Upload className="w-3.5 h-3.5" /><span>上传已有试卷模板</span></> : <><Layers className="w-3.5 h-3.5" /><span>精选参考示例模板</span></>}</button>)}</div><button type="button" onClick={onDownloadSample} className="text-xs text-brand-600 hover:text-brand-700 font-medium flex items-center gap-1 mb-2 hover:underline cursor-pointer" title="下载空白试卷结构模板说明"><Download className="w-3.5 h-3.5" /><span>下载结构范例文件</span></button></div>
      <div className="p-6 overflow-y-auto flex-1 space-y-5">{children}</div>
      <div className="px-6 py-3 border-t border-slate-200 bg-slate-50/50 flex items-center justify-between text-xs text-slate-500"><div>💡 套用模板后，系统将自动调整试卷题型、分值与考试时间，保留当前选定教材章节。</div><button type="button" onClick={onClose} className="px-5 py-2 border border-slate-300 hover:bg-slate-100 rounded-xl text-slate-700 font-semibold text-xs transition cursor-pointer">关闭</button></div>
    </div>
  </div>
);
