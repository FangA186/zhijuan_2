import React from 'react';
import { selectionLabels } from '../../lib/answerScoring';
import { AnswerScoring } from '../../components/AnswerScoring';
import { AlertTriangle, CheckCircle2, ShieldCheck } from 'lucide-react';
import { GeneratedCandidate } from '../../types/candidate';
import { ValidationRecord } from '../../types/validation';
import { MathRenderer } from '../../lib/math';
import { StatusBadge } from '../../components/StatusBadge';

type Tab = 'answer' | 'blind_solve' | 'evidence';
interface Props {
  candidate: GeneratedCandidate;
  validation: ValidationRecord | null;
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
}

export const ExamEditorEvidence: React.FC<Props> = ({ candidate, validation, activeTab, onTabChange }) => (
  <div className="lg:col-span-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
    <div className="flex rounded-xl bg-slate-100 p-1 text-xs font-medium text-slate-600">
      {(['answer', 'blind_solve', 'evidence'] as const).map(tab => (
        <button key={tab} onClick={() => onTabChange(tab)} className={`flex-1 py-1.5 rounded-lg transition ${activeTab === tab ? 'bg-white text-slate-900 font-bold shadow-xs' : 'hover:text-slate-900'}`}>
          {tab === 'answer' ? '参考答案与细则' : tab === 'blind_solve' ? '双重验算对比' : '智能质检与规范核验'}
        </button>
      ))}
    </div>
    {activeTab === 'answer' && (
      <div className="space-y-4 text-xs">
        {(candidate.private?.answers || []).map((ans: any, idx: number) => {
          const answerText = selectionLabels(candidate.public, ans).join('、') || ans.answer_text || ans.accepted_answers?.[0]?.value || '见详细解析过程';
          const explanation = ans.explanation || ans.solution || [];
          return (
            <div key={idx} className="space-y-3">
              <div className="p-3 bg-brand-50/70 border border-brand-200 rounded-xl space-y-1.5">
                <span className="text-[11px] font-bold text-brand-800 block">标准参考答案:</span>
                <span className="font-mono text-sm font-bold text-brand-900 bg-white px-2 py-0.5 rounded border border-brand-200 inline-block">{answerText}</span>
              </div>
              <div className="space-y-1">
                <span className="text-[11px] font-bold text-slate-700 block">详细解析过程:</span>
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl leading-relaxed"><MathRenderer content={explanation} /></div>
              </div>
              <AnswerScoring question={candidate.public} answer={ans} />
            </div>
          );
        })}
      </div>
    )}
    {activeTab === 'blind_solve' && validation && (
      <div className="space-y-4 text-xs">
        <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-xl space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-bold text-indigo-900">独立做题教师验算报告</span>
            {validation.blind_solve.is_same_model && <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-200/80 text-indigo-900 font-bold">独立推理隔离</span>}
          </div>
          <div className="text-[11px] text-indigo-700 leading-relaxed">独立做题教师在严格屏蔽出题参考答案的环境中独立推理解题，耗时 {validation.blind_solve.duration_ms} ms。</div>
        </div>
        <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
          <div className="flex justify-between items-center"><span className="text-slate-500">独立做题推导答案:</span><span className="font-mono font-bold text-slate-900">{validation.blind_solve.derived_answer}</span></div>
          <div className="flex justify-between items-center border-t border-slate-200 pt-1.5">
            <span className="text-slate-500">与出题答案比对:</span>
            {validation.blind_solve.match_reference ? <span className="text-emerald-600 font-bold flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" />验算完全一致</span> : <span className="text-rose-600 font-bold flex items-center gap-1"><AlertTriangle className="w-3.5 h-3.5" />需教师核对</span>}
          </div>
        </div>
        <div className="space-y-1.5">
          <span className="text-[11px] font-bold text-slate-700 block">独立做题解题推演步骤:</span>
          <div className="space-y-1">{(validation.blind_solve?.steps || []).map(step => <div key={step.step_number} className="p-2 rounded bg-slate-50 text-[11px] text-slate-600"><span className="font-semibold text-slate-800">步骤 {step.step_number}: </span>{step.description}</div>)}</div>
        </div>
      </div>
    )}
    {activeTab === 'evidence' && validation && (
      <div className="space-y-3 text-xs">
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl space-y-1 text-emerald-900">
          <div className="font-bold flex items-center gap-1"><ShieldCheck className="w-4 h-4 text-emerald-600" />智能质检与考点规范依据</div>
          <div className="text-[11px] text-emerald-700">基于国家课标知识点规范与严谨数学符号推导，双重核实题意严密性。</div>
        </div>
        <div className="space-y-2">{(validation.rule_checks || []).map(rule => (
          <div key={rule.rule_id} className="p-3 rounded-xl border border-slate-200 bg-slate-50 space-y-1.5">
            <div className="flex items-center justify-between"><span className="font-bold text-slate-900">{rule.name}</span><StatusBadge status={rule.status} /></div>
            <p className="text-[11px] text-slate-600">{rule.detail}</p>
            {rule.evidence && <div className="font-mono text-[10px] bg-slate-200/60 p-1.5 rounded text-slate-800">依据: {rule.evidence}</div>}
          </div>
        ))}</div>
        <div className="text-[10px] text-slate-400 font-mono pt-2 border-t border-slate-100">题目防篡改指纹: {validation.content_hash}</div>
      </div>
    )}
  </div>
);
