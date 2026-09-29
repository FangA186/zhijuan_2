import React, { useEffect, useRef } from 'react';
import type { FoolproofSetupModel } from './FoolproofSetupModel';

export const ScopeSwitchDialog: React.FC<{ model: FoolproofSetupModel }> = ({ model }) => {
  const { pendingScopeSwitch, setPendingScopeSwitch, confirmScopeSwitch } = model;
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (pendingScopeSwitch && !dialog.current?.open) dialog.current?.showModal();
  }, [pendingScopeSwitch]);
  if (!pendingScopeSwitch) return null;
  return (
    <dialog ref={dialog} aria-labelledby="scope-switch-title"
      onCancel={() => setPendingScopeSwitch(null)}
      className="w-[calc(100%-2rem)] max-w-xl max-h-[90dvh] rounded-2xl border border-amber-200 p-0 shadow-xl backdrop:bg-slate-900/60">
      <div className="flex max-h-[90dvh] flex-col p-5 text-sm text-amber-900 gap-4">
        <h2 id="scope-switch-title" className="font-bold text-lg">确认切换学段或教材</h2>
        <p>即将切换至 {pendingScopeSwitch.nextSpec.grade_label} · {pendingScopeSwitch.nextSpec.textbook || '未选择教材'}。请选择如何处理旧考查范围。</p>
        <div className="min-h-0 overflow-y-auto break-words rounded-lg bg-amber-50 p-3">
              <div className="text-xs text-amber-800">
                {pendingScopeSwitch.staleTextbook.length > 0 && (
                  <div>· 随旧教材章节带入（建议清除）：{pendingScopeSwitch.staleTextbook.join('、')}</div>
                )}
                {pendingScopeSwitch.staleTemplate.length > 0 && (
                  <div>· 随模板建议带入（建议清除）：{pendingScopeSwitch.staleTemplate.join('、')}</div>
                )}
                {pendingScopeSwitch.manual.length > 0 && (
                  <div>· 手动补充项（将始终保留，请自行判断是否适用）：{pendingScopeSwitch.manual.join('、')}</div>
                )}
                {pendingScopeSwitch.staleTextbook.length === 0 && pendingScopeSwitch.staleTemplate.length === 0 && (
                  <div>当前没有带来源标记的旧范围项，仅保留手动补充项。</div>
                )}
              </div>
        </div>
        <p className="text-xs">手动补充项不会被自动删除；切换后需重新确认考查范围。</p>
        <div className="flex flex-wrap gap-2 shrink-0">
          <button type="button" autoFocus onClick={() => setPendingScopeSwitch(null)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-slate-700">取消切换</button>
          <button type="button" onClick={() => confirmScopeSwitch('clear')}
            className="rounded-lg bg-brand-600 px-3 py-2 text-white">清除失效项后继续</button>
          <button type="button" onClick={() => confirmScopeSwitch('keep')}
            className="rounded-lg border border-slate-300 px-3 py-2 text-slate-700">保留旧范围全部项</button>
        </div>
      </div>
    </dialog>
  );
};
