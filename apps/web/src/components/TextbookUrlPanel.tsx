import React from 'react';
import { TextbookSummary } from '../types/spec';

interface TextbookUrlPanelProps {
  urlInput: string;
  urlError: string;
  matchedMaterial: TextbookSummary | null;
  onInputChange: (value: string) => void;
  onParse: () => void;
  onChoose: (material: TextbookSummary) => void;
}

export const TextbookUrlPanel: React.FC<TextbookUrlPanelProps> = ({ urlInput, urlError, matchedMaterial, onInputChange, onParse, onChoose }) => (
  <div className="space-y-4">
    <p className="text-xs text-slate-600">支持直接粘贴国家中小学智慧教育平台（<code>basic.smartedu.cn</code>）课程链接，智能解析 <code>defaultTag</code> 标签链并锁定教材：</p>
    <div className="flex gap-2"><input type="text" value={urlInput} onChange={(event) => onInputChange(event.target.value)} placeholder="如：https://basic.smartedu.cn/syncClassroom?defaultTag=e7bbcefe-0590-11ed...%2F5036342972" className="flex-1 px-3 py-2 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-brand-500 focus:outline-hidden font-mono" /><button type="button" onClick={onParse} className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-xl transition shrink-0">解析并匹配</button></div>
    {urlError && <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700">{urlError}</div>}
    {matchedMaterial && <div className="p-4 rounded-xl border border-emerald-300 bg-emerald-50/50 flex items-center justify-between gap-4"><div><div className="text-xs font-bold text-emerald-800 mb-1">🎉 成功解析并匹配到国家教材：</div><div className="text-sm font-bold text-slate-900">{matchedMaterial.title}</div><div className="text-xs text-slate-500 font-mono mt-0.5">ID: {matchedMaterial.id}</div></div><button type="button" onClick={() => onChoose(matchedMaterial)} className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-xs transition shrink-0">确认选用该教材</button></div>}
  </div>
);
