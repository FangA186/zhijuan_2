import React from 'react';
import { Hash } from 'lucide-react';

export const ReviewIntegrity: React.FC = () => (
  <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
    <h3 className="font-bold text-sm text-slate-900 flex items-center gap-2">
      <Hash className="w-4 h-4 text-brand-600" />
      试卷内容防篡改与印刷质量核验
    </h3>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
      <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
        <div className="text-slate-500 font-sans font-semibold">试卷内容指纹:</div>
        <div className="text-slate-800 break-all">sha256:4a81cf208a0029bc41d2f...b983a0194e1e</div>
        <div className="text-[10px] text-emerald-700 font-sans">✓ 题面、选项、答案与给分点已固化防篡改</div>
      </div>
      <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
        <div className="text-slate-500 font-sans font-semibold">排版一致性指纹:</div>
        <div className="text-slate-800 break-all">render_sha256:9c12e8401aa89f1...29c491aa2810</div>
        <div className="text-[10px] text-emerald-700 font-sans">✓ 预检 A4 双栏印刷与 PDF 导出版面完整一致</div>
      </div>
    </div>
  </div>
);
