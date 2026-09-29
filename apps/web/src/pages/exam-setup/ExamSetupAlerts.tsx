import { AlertTriangle, RefreshCw } from 'lucide-react';
import { GenerationRuntimeState } from '../../types/job';
import { PendingScopeSwitch } from './ExamSetupTypes';
import { ScopeSwitchMode } from '../../lib/sectionScope';

interface Props {
  readiness: GenerationRuntimeState | null;
  readinessChecking: boolean;
  confirmBlockers: { label: string; hint: string }[];
  scopeNotice: string;
  pendingScopeSwitch: PendingScopeSwitch | null;
  onConfirmScopeSwitch: (mode: ScopeSwitchMode) => void;
}

export function ExamSetupAlerts({
  readiness, readinessChecking, confirmBlockers, scopeNotice, pendingScopeSwitch, onConfirmScopeSwitch,
}: Props) {
  return (
    <>
      {(readinessChecking || (readiness !== null && readiness.versionConfirmed && readiness.ready !== true) || confirmBlockers.length > 0) && (
        <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm space-y-1.5">
          {readinessChecking ? (
            <div className="text-xs text-slate-500 flex items-center gap-2">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-brand-500" /> 正在检查生成服务就绪状态…
            </div>
          ) : (
            <>
              <div className="font-semibold text-amber-900 flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-600" /> 确认蓝图暂不可用，原因如下（逐项下一步提示）
              </div>
              {confirmBlockers.map((blocker) => (
                <div key={blocker.label} className="text-xs text-amber-900">
                  <span className="font-bold">· {blocker.label}</span>
                  <span className="text-amber-700 ml-1.5">{blocker.hint}</span>
                </div>
              ))}
            </>
          )}
        </div>
      )}
      {scopeNotice && <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 whitespace-pre-line">{scopeNotice}</div>}
      {pendingScopeSwitch && (
        <div role="alert" className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 space-y-2">
          <div className="font-semibold flex items-center gap-1.5"><AlertTriangle className="w-4 h-4 text-amber-600" /> 学段/教材已变更，以下旧范围项可能失效</div>
          <div className="text-xs text-amber-800">
            {pendingScopeSwitch.staleTextbook.length > 0 && (
              <div>· 随旧教材章节/模板带入（建议清除）：{pendingScopeSwitch.staleTextbook.join('、')}</div>
            )}
            {pendingScopeSwitch.manual.length > 0 && (
              <div>· 手动补充项（将始终保留，请自行判断是否适用）：{pendingScopeSwitch.manual.join('、')}</div>
            )}
            {pendingScopeSwitch.staleTextbook.length === 0 && (
              <div>当前没有带来源标记的旧范围项，仅保留手动补充项。</div>
            )}
          </div>
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={() => onConfirmScopeSwitch('clear')}
              className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-lg cursor-pointer"
            >
              清除失效项后继续
            </button>
            <button
              type="button"
              onClick={() => onConfirmScopeSwitch('keep')}
              className="px-3 py-1.5 bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 text-xs font-bold rounded-lg cursor-pointer"
            >
              保留旧范围全部项
            </button>
          </div>
          <div className="text-[11px] text-amber-700">两种选择都不会静默删除手动补充项，也都会强制重新勾选「我已确认本次考查范围」后再出卷。</div>
        </div>
      )}
    </>
  );
}

