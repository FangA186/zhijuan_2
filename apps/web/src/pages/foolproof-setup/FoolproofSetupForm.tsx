import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { calculateSectionsTotalX100, formatScoreX100 } from '../../lib/scoring';
import { reasonLabel } from '../../lib/runtimeReasons';
import { FoolproofSetupBasics } from './FoolproofSetupBasics';
import { FoolproofSetupScope } from './FoolproofSetupScope';
import { FoolproofSetupActions } from './FoolproofSetupActions';
import { FoolproofSetupModals } from './FoolproofSetupModals';
import { useFoolproofSetupScope } from './useFoolproofSetupScope';
import { useFoolproofSetupGeneration } from './useFoolproofSetupGeneration';
import type { LoadedFoolproofSetupState } from './useFoolproofSetupBase';
import type { FoolproofSetupModel } from './FoolproofSetupModel';

interface Props { state: LoadedFoolproofSetupState; generationConfigured: boolean; onStartGeneration: (spec: LoadedFoolproofSetupState['spec']) => void; }
export const FoolproofSetupForm: React.FC<Props> = ({ state, generationConfigured, onStartGeneration }) => {
  const scope = useFoolproofSetupScope(state);
  const generation = useFoolproofSetupGeneration(state, scope.isChinese, onStartGeneration);
  const { spec, readinessChecking, readiness, scopeNotice } = state;
  const { issuesList } = generation;
  const model: FoolproofSetupModel = { ...state, ...scope, ...generation };
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      {!generationConfigured && <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">当前可编辑出卷配置和预览题槽计划。生成服务尚未配置完整，暂不能开始出题。</div>}
      {readinessChecking ? (
        <div role="status" className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500 flex items-center gap-2">
          <RefreshCw className="w-3.5 h-3.5 animate-spin text-brand-500" /> 正在检查生成服务就绪状态…
        </div>
      ) : readiness !== null && readiness.versionConfirmed && readiness.ready !== true ? (
        <div role="status" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900 space-y-1.5">
          <div className="font-semibold flex items-center gap-1.5"><AlertTriangle className="w-4 h-4 text-rose-600" /> 生成服务当前未就绪，暂不能开始命题</div>
          {readiness.reasonCodes.map((code) => (
            <div key={code} className="text-xs pl-1">
              · {reasonLabel(code)} <span className="text-rose-400">（{code}）</span>
            </div>
          ))}
          {readiness.reasonCodes.length === 0 && (
            <div className="text-xs pl-1">未返回具体原因（版本未确认），请确认服务版本后点击下方「重新检查生成服务」。</div>
          )}
        </div>
      ) : null}
      {scopeNotice && <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 whitespace-pre-line">{scopeNotice}</div>}
      <section aria-label="分值核对" className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
        <h2 className="font-semibold">当前分值核对</h2>
        {issuesList.length > 0 ? (
          <ul className="mt-1 space-y-1 text-rose-700 list-disc pl-4">
            {issuesList.map((msg, i) => <li key={i}>{msg}</li>)}
          </ul>
        ) : (
          <p className="mt-1 text-emerald-700">各题组逐题分值已核对，题型合计 {formatScoreX100(calculateSectionsTotalX100(spec.sections))} 分 / 试卷设定 {formatScoreX100(spec.total_score_x100)} 分</p>
        )}
      </section>
      {/* 顶部标题 */}
      <div className="text-center py-2">
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
          智能试卷生成
        </h1>
      </div>

      {/* 核心卡片容器 */}
      <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 sm:p-8 space-y-8">
        <FoolproofSetupBasics model={model} />
        <FoolproofSetupScope model={model} />
        <FoolproofSetupActions model={model} />
        <FoolproofSetupModals model={model} />
      </div>
    </div>
  );
};
