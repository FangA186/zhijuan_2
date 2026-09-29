import React from 'react';
import { MultipleChoiceScoringField } from '../../components/MultipleChoiceScoringField';
import { BookOpen, FileUp } from 'lucide-react';
import { formatScoreX100 } from '../../lib/scoring';
import { PRESET_DEFINITIONS } from './foolproofSetupPresets';
import type { FoolproofSetupModel } from './FoolproofSetupModel';
import { gradeLabelForStage } from '../../lib/stageYear';
import type { Stage } from '../../types/spec';

export const FoolproofSetupBasics: React.FC<{ model: FoolproofSetupModel }> = ({ model }) => {
  const { spec, setSpec, setIsTextbookModalOpen, presetType, templateApplied, handleSelectPreset, handleStageSelect, totalQuestions, computePresetSummary } = model;
  return (
    <>
        {/* 第 1 步：学段与年级学科 */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-brand-600 text-white flex items-center justify-center font-bold text-xs">
              1
            </span>
            <h2 className="text-base font-bold text-slate-900">选择学段与教材</h2>
          </div>

          {/* 学段药丸按钮 */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { id: 'primary', label: '小学 (1~6年级)', desc: '基础概念、直观理解' },
              { id: 'junior', label: '初中 (7~9年级)', desc: '代数几何、逻辑推理' },
              { id: 'senior', label: '高中 (高一~高三)', desc: '函数向量、综合探究' },
            ].map((stg) => (
              <button
                key={stg.id}
                type="button"
                onClick={() => handleStageSelect(stg.id as Stage)}
                className={`p-3.5 rounded-2xl border text-left transition-all cursor-pointer ${
                  spec.stage === stg.id
                    ? 'border-brand-600 bg-brand-50/60 ring-2 ring-brand-500/20 text-brand-900 shadow-xs'
                    : 'border-slate-200 hover:border-slate-300 text-slate-700 bg-white'
                }`}
              >
                <div className="font-bold text-sm">{stg.label}</div>
                <div className="text-xs text-slate-500 mt-1">{stg.desc}</div>
              </button>
            ))}
          </div>

          {/* 当前教材与年级卡片 */}
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-brand-100 text-brand-700 flex items-center justify-center font-bold text-sm shrink-0">
                <BookOpen className="w-5 h-5" />
              </div>
              <div>
                <div className="font-bold text-sm text-slate-900">
                  {spec.material_id ? (spec.textbook || '已选择教材') : '未选择教材'}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  {spec.material_id ? '已选教材，请核对年级' : '尚未选择教材，可从下方选择'}
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setIsTextbookModalOpen(true)}
              className="px-3.5 py-2 bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 font-semibold text-xs rounded-xl shadow-2xs transition flex items-center gap-1.5 shrink-0 self-start sm:self-auto cursor-pointer"
            >
              <BookOpen className="w-3.5 h-3.5 text-brand-600" />
              <span>切换教材版本</span>
            </button>
          </div>
          <label className="block text-sm text-slate-700">
            年级（请选择并确认）
            <select value={spec.stage_year} onChange={(event) => {
              const year = Number(event.target.value);
              setSpec({ ...spec, stage_year: year, grade_label: gradeLabelForStage(spec.stage, year),
                material_id: undefined, textbook_cover: undefined, textbook: null,
                taught_scope: { ...spec.taught_scope, scope_confirmed: false } });
            }} className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2">
              {Array.from({ length: spec.stage === 'primary' ? 6 : 3 }, (_, index) => index + 1).map(year =>
                <option key={year} value={year}>{gradeLabelForStage(spec.stage, year)}</option>)}
            </select>
          </label>
        </div>

        {/* 第 2 步：试卷类型与分值 */}
        <div className="space-y-4 pt-4 border-t border-slate-100">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-brand-600 text-white flex items-center justify-center font-bold text-xs">
              2
            </span>
            <h2 className="text-base font-bold text-slate-900">选择试卷规格</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {PRESET_DEFINITIONS.map((p) => {
              const desc = computePresetSummary(p, spec.taught_scope?.topics?.length || 0);
              const isSelected = !templateApplied && presetType === p.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => handleSelectPreset(p.id as any)}
                  className={`p-4 rounded-2xl border text-left transition-all relative cursor-pointer ${
                    isSelected
                      ? 'border-brand-600 bg-brand-50/60 ring-2 ring-brand-500/20 shadow-xs'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  {p.isBest && (
                    <span className="absolute -top-2.5 right-3 px-2 py-0.5 rounded-full text-[10px] font-bold bg-brand-600 text-white shadow-2xs">
                      ★ {p.badge}
                    </span>
                  )}
                  {!p.isBest && (
                    <span className="absolute -top-2.5 right-3 px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                      {p.badge}
                    </span>
                  )}
                  <div className="font-bold text-sm text-slate-900">{p.title}</div>
                  <div className="text-xs text-slate-500 mt-1">{desc}</div>
                </button>
              );
            })}
          </div>
          {templateApplied && (
            <div className="rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3 text-xs text-indigo-900 flex items-center gap-2">
              <FileUp className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
              <span>当前套用的是{templateApplied.source === 'uploaded' ? '上传的' : '精选'}「{templateApplied.name}」模板——按自定义模板出卷，不再按上方预设（题数 {totalQuestions} 题、时长 {spec.duration_minutes ?? '—'} 分钟、满分 {formatScoreX100(spec.total_score_x100)} 分）。如需回到快捷预设，点击对应卡片即可。</span>
            </div>
          )}

          <MultipleChoiceScoringField spec={spec} setSpec={setSpec} />
          {/* 试卷标题微调 */}
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">试卷大标题（将打印在试卷卷头）</label>
            <input
              type="text"
              value={spec.title}
              onChange={(e) => setSpec({ ...spec, title: e.target.value })}
              className="w-full border border-slate-300 rounded-xl px-3.5 py-2 text-sm text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden font-medium"
            />
          </div>
        </div>


    </>
  );
};
