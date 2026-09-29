import { Dispatch, SetStateAction } from 'react';
import { AlertCircle, CheckCircle, Edit3 } from 'lucide-react';
import { BlueprintSlot, ExamBlueprint, ExamSpec } from '../../types/spec';
import { formatScoreX100 } from '../../lib/scoring';
import { SlotEditorModal } from '../../components/SlotEditorModal';

interface Props {
  spec: ExamSpec;
  blueprint: ExamBlueprint | null;
  editingSlot: BlueprintSlot | null;
  setEditingSlot: Dispatch<SetStateAction<BlueprintSlot | null>>;
  setBlueprint: Dispatch<SetStateAction<ExamBlueprint | null>>;
  scoreBalance: { isBalanced: boolean; actualTotalX100: number; diffX100: number };
}

export function ExamSetupSummary({ spec, blueprint, editingSlot, setEditingSlot, setBlueprint, scoreBalance }: Props) {
  return (
    <>
      <div className="space-y-6">
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h3 className="text-base font-bold text-slate-900">卷面分值平衡校验器</h3>
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3 text-sm">
            <div className="flex justify-between items-center">
              <span className="text-slate-500">目标满分:</span>
              <span className="font-bold text-slate-900 text-lg">{formatScoreX100(spec.total_score_x100)} 分</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-500">当前各题合计:</span>
              <span className="font-bold text-slate-900 text-lg">{formatScoreX100(scoreBalance.actualTotalX100)} 分</span>
            </div>
            <div className="border-t border-slate-200 pt-2 flex items-center justify-between">
              <span className="text-xs text-slate-500">配平结果:</span>
              {scoreBalance.isBalanced ? (
                <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                  <CheckCircle className="w-3.5 h-3.5" />完全平衡 (0 误差)
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-xs font-bold text-rose-700 bg-rose-100 px-2 py-0.5 rounded-full">
                  <AlertCircle className="w-3.5 h-3.5" />相差 {formatScoreX100(Math.abs(scoreBalance.diffX100))} 分
                </span>
              )}
            </div>
          </div>
          {!scoreBalance.isBalanced && <p className="text-xs text-rose-600 leading-relaxed">
            * 注意：总分矛盾将在调用任何模型前被直接拦截。请调整题量或单题分值以配平。
          </p>}
        </div>

        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-slate-900">AI 规划槽位表 ({blueprint?.slots.length || 0} 题)</h3>
            <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded font-mono">Rev #{blueprint?.revision || 1}</span>
          </div>
          <div className="max-h-[420px] overflow-y-auto space-y-2 pr-1">
            {blueprint?.slots.map((slot) => (
              <div key={slot.slot_id} className="p-3 rounded-xl border border-slate-200 hover:border-brand-400 bg-white transition flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-slate-100 text-slate-700 flex items-center justify-center font-bold text-[11px] shrink-0">{slot.order}</span>
                  <div><div className="font-semibold text-slate-900">{slot.target_topic}</div><div className="text-slate-400 text-[11px]">{slot.cognitive_target}</div></div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold text-[11px]">{formatScoreX100(slot.score_x100)}分</span>
                  <button onClick={() => setEditingSlot(slot)} className="p-1 text-slate-400 hover:text-brand-600 rounded transition" title="微调此槽位">
                    <Edit3 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <SlotEditorModal
        slot={editingSlot}
        onClose={() => setEditingSlot(null)}
        onSave={(updated) => {
          if (!blueprint) return;
          setBlueprint({ ...blueprint, slots: blueprint.slots.map((slot) =>
            slot.slot_id === updated.slot_id ? updated : slot) });
        }}
      />
    </>
  );
}

