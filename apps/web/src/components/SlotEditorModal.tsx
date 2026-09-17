import React, { useState } from 'react';
import { X, Save } from 'lucide-react';
import { BlueprintSlot, QuestionKind } from '../types/spec';
import { formatScoreX100, parseScoreToX100 } from '../lib/scoring';

interface SlotEditorModalProps {
  slot: BlueprintSlot | null;
  onClose: () => void;
  onSave: (updatedSlot: BlueprintSlot) => void;
}

export const SlotEditorModal: React.FC<SlotEditorModalProps> = ({
  slot,
  onClose,
  onSave,
}) => {
  if (!slot) return null;

  const [kind, setKind] = useState<QuestionKind>(slot.kind);
  const [topic, setTopic] = useState(slot.target_topic);
  const [cognitive, setCognitive] = useState(slot.cognitive_target);
  const [difficulty, setDifficulty] = useState<'basic' | 'medium' | 'advanced'>(slot.estimated_difficulty);
  const [scoreStr, setScoreStr] = useState(formatScoreX100(slot.score_x100));
  const [lines, setLines] = useState(slot.answer_space_lines);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      ...slot,
      kind,
      target_topic: topic,
      cognitive_target: cognitive,
      estimated_difficulty: difficulty,
      score_x100: parseScoreToX100(scoreStr),
      answer_space_lines: lines,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <h3 className="text-base font-bold text-slate-900">
            微调蓝图槽位 (Slot: #{slot.order} - {slot.slot_id})
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-sm">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">题型种类</label>
            <select
              value={kind}
              onChange={(e) => setKind(e.target.value as QuestionKind)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
            >
              <option value="single_choice">单项选择题 (single_choice)</option>
              <option value="multiple_choice">多项选择题 (multiple_choice)</option>
              <option value="true_false">判断题 (true_false)</option>
              <option value="fill_blank">填空题 (fill_blank)</option>
              <option value="solution">计算与解答题 (solution)</option>
              <option value="short_answer">简答题 (short_answer)</option>
              <option value="essay">作文/论述 (essay)</option>
              <option value="material_group">材料综合题组 (material_group)</option>
            </select>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">考查核心知识点</label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              required
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">难度倾向</label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value as any)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
              >
                <option value="basic">基础题 (basic)</option>
                <option value="medium">中等难度 (medium)</option>
                <option value="advanced">综合拔高 (advanced)</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">分值 (分)</label>
              <input
                type="number"
                step="0.5"
                min="1"
                value={scoreStr}
                onChange={(e) => setScoreStr(e.target.value)}
                required
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
              />
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">考查认知目标</label>
            <input
              type="text"
              value={cognitive}
              onChange={(e) => setCognitive(e.target.value)}
              placeholder="如：理解与辨析 / 代数运算 / 几何推理"
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">答题空间预留 (行数)</label>
            <input
              type="number"
              min="0"
              max="50"
              value={lines}
              onChange={(e) => setLines(Number(e.target.value))}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
            />
          </div>

          <div className="pt-3 border-t border-slate-200 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-slate-600 hover:text-slate-800 font-medium"
            >
              取消
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white font-bold rounded-lg flex items-center gap-1.5 shadow-sm"
            >
              <Save className="w-4 h-4" />
              保存槽位设置
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
