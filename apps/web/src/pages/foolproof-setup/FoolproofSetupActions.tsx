import { AgentActivityConsole } from '../job-progress/AgentActivityConsole';
import { questionKindLabel } from '../job-progress/jobProgressHelpers';
import React from 'react';
import { Sparkles, FileUp, RefreshCw } from 'lucide-react';
import { api } from '../../lib/api';
import type { FoolproofSetupModel } from './FoolproofSetupModel';

export const FoolproofSetupActions: React.FC<{ model: FoolproofSetupModel }> = ({ model }) => {
  const { spec, setIsTemplateModalOpen, isSubmitting, preview, previewSpec, setReadiness, setReadinessChecking, startInFlight, handleOneClickGenerate, handleConfirmAndStart, confirmBlockers, canStart, totalQuestions, totalScore } = model;
  return (
    <>
        {/* 核心生成大按钮与试卷模板参考 */}
        <div className="pt-4 border-t border-slate-100 space-y-3">
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              type="button"
              onClick={handleOneClickGenerate}
              disabled={isSubmitting || model.planningBusy}
              className="flex-1 py-4 bg-brand-600 hover:bg-brand-700 active:scale-[0.99] text-white font-bold text-base rounded-2xl shadow-md shadow-brand-500/20 transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            >
              <Sparkles className={`w-5 h-5 text-amber-300 ${isSubmitting ? 'animate-spin' : ''}`} />
              <span>{model.planningBusy ? '规划 Agent 执行中…' : isSubmitting ? '正在保存配置…' : '让规划 Agent 设计蓝图'}</span>
            </button>

            <button
              type="button"
              onClick={() => setIsTemplateModalOpen(true)}
              className="px-5 py-3.5 sm:py-4 bg-slate-50 hover:bg-slate-100 active:bg-slate-200 border border-slate-200 hover:border-slate-300 text-slate-700 font-bold text-sm rounded-2xl transition-all flex items-center justify-center gap-2 cursor-pointer shrink-0 shadow-2xs"
            >
              <FileUp className="w-4 h-4 text-brand-600" />
              <span>上传试卷模板参考示例</span>
            </button>
          </div>

          <p className="text-xs text-slate-500">规划将调用模型并计入用量；设计完成后先核对蓝图，再确认出题。</p>
          {model.planningError && <p role="alert" className="text-sm text-rose-700">{model.planningError}</p>}
          {model.planning && <>
            <AgentActivityConsole logs={model.planning.activity || []}
              terminal={!['QUEUED', 'RUNNING'].includes(model.planning.status)}
              status={`规划：${model.planning.status}${model.planning.stale ? ' · 配置已改变，此结果不可应用' : ''}${model.planning.error ? ' · ' + model.planning.error : ''}`} />
            {['QUEUED', 'RUNNING'].includes(model.planning.status) && <button type="button" onClick={model.cancelPlanning} className="text-sm underline">停止规划</button>}
          </>}
          <div className="flex justify-end">
            <button
              type="button"
              onClick={async () => {
                setReadinessChecking(true);
                const state = await api.fetchGenerationReadiness();
                setReadiness(state);
                setReadinessChecking(false);
              }}
              className="text-xs text-brand-600 hover:text-brand-700 font-medium flex items-center gap-1 cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" /> 重新检查生成服务
            </button>
          </div>

          {preview && JSON.stringify(spec) === previewSpec && (
            <div className="rounded-xl border border-brand-200 bg-brand-50 p-4 space-y-3">
              <h3 className="font-semibold text-slate-900">请核对本次题槽计划（{preview.slots.length} 题）</h3>
              {preview.planning_summary && <p className="text-sm text-slate-700 whitespace-pre-wrap">{preview.planning_summary}</p>}
              <div className="max-h-80 overflow-y-auto text-sm text-slate-700 space-y-1">
                {preview.slots.map(slot => <div key={slot.slot_id}>第 {slot.order} 题 · {slot.target_topic} · {questionKindLabel(slot.kind)} · {slot.score_x100 / 100} 分 · {{ basic: '基础', medium: '中等', advanced: '较难' }[slot.estimated_difficulty]}
                  {slot.design_brief && <p className="mt-1 text-slate-600">{slot.design_brief}</p>}
                  {slot.planning_rationale && <p className="text-xs text-slate-500 mb-3">设计依据：{slot.planning_rationale}</p>}
                </div>)}
              </div>
              {!!spec.taught_scope?.scope_confirmed && confirmBlockers.length === 0 && (
                <p role="status" className="text-xs text-emerald-800">生成服务已就绪、范围已确认、计划为最新版本，可开始命题。</p>
              )}
              {confirmBlockers.length > 0 && (
                <div role="status" className="rounded-lg bg-white/70 border border-amber-200 p-2.5 space-y-1">
                  {confirmBlockers.map((b) => (
                    <div key={b.label} className="text-xs text-amber-900">
                      <span className="font-bold">· {b.label}</span>
                      <span className="text-amber-700 ml-1.5">{b.hint}</span>
                    </div>
                  ))}
                </div>
              )}
              <button type="button" onClick={handleConfirmAndStart} disabled={!canStart}
                className="rounded-lg bg-brand-600 px-5 py-2 text-white font-semibold disabled:opacity-50">
                {startInFlight.current && !isSubmitting ? '启动结果未知，请刷新' : isSubmitting ? '正在启动...' : '确认计划并开始命题'}
              </button>
            </div>
          )}

          <div className="text-center text-xs text-slate-400 flex items-center justify-center gap-4 flex-wrap">
            <span>✓ 全卷共 {totalQuestions} 道题</span>
            <span>✓ 满分 {totalScore} 分</span>
            <span>✓ 生成后需检查题目</span>
            <span>✓ 生成后直接呈现 A4 打印卷</span>
          </div>
        </div>
    </>
  );
};
