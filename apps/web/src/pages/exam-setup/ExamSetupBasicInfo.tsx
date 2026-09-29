import { Dispatch, SetStateAction } from 'react';
import { BookOpen } from 'lucide-react';
import { ExamSpec, Stage } from '../../types/spec';
import { gradeLabelForStage, subjectCodeFromLabel } from '../../lib/stageYear';

interface Props {
  spec: ExamSpec;
  setSpec: Dispatch<SetStateAction<ExamSpec | null>>;
  onOpenTextbooks: () => void;
  onStageChange: (stage: Stage) => void;
}

export function ExamSetupBasicInfo({ spec, setSpec, onOpenTextbooks, onStageChange }: Props) {
  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-brand-500"></span>
          1. 基础信息与教材选用 (国家智慧教育平台标准)
        </h2>
        <button
          type="button"
          onClick={onOpenTextbooks}
          className="px-3 py-1.5 bg-brand-50 hover:bg-brand-100 text-brand-700 font-semibold text-xs rounded-xl border border-brand-200 transition flex items-center gap-1.5 shadow-2xs"
        >
          <BookOpen className="w-3.5 h-3.5 text-brand-600" />
          <span>{spec.material_id ? '更换教材' : '切换/选用教材'}</span>
        </button>
      </div>

      {spec.material_id ? (
        <div className="p-4 rounded-xl border border-brand-200 bg-gradient-to-r from-brand-50/70 via-indigo-50/40 to-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            {spec.textbook_cover ? (
              <img
                src={spec.textbook_cover}
                alt="教材封面"
                className="w-12 h-16 object-cover rounded-lg shadow-xs border border-slate-200 shrink-0 bg-white"
                onError={(event) => { (event.target as HTMLElement).style.display = 'none'; }}
              />
            ) : (
              <div className="w-12 h-16 rounded-lg bg-brand-100 text-brand-700 flex flex-col items-center justify-center font-bold text-xs shrink-0 border border-brand-200">
                <BookOpen className="w-5 h-5 mb-1" /><span>教材</span>
              </div>
            )}
            <div>
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-brand-600 text-white shadow-2xs">国家智慧教育平台教材</span>
                <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800">章节大纲已联动</span>
              </div>
              <div className="font-bold text-slate-900 text-sm">{spec.textbook || spec.title}</div>
              <div className="text-xs text-slate-500 mt-0.5">{spec.subject_label} · {spec.grade_label} · {spec.curriculum_system}</div>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={onOpenTextbooks}
              className="px-3 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 font-semibold text-xs rounded-xl shadow-2xs transition flex items-center gap-1.5"
            >
              <BookOpen className="w-3.5 h-3.5 text-brand-600" /><span>更换教材</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="p-4 rounded-xl border border-dashed border-slate-300 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center shrink-0"><BookOpen className="w-5 h-5" /></div>
            <div>
              <div className="font-bold text-sm text-slate-800">快速从国家中小学智慧教育平台选用教材</div>
              <div className="text-xs text-slate-500">同步 3,200+ 本官方教材目录大纲，自动填充学段学科，并在下方一键勾选章节出题。</div>
            </div>
          </div>
          <button
            type="button"
            onClick={onOpenTextbooks}
            className="px-3.5 py-2 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-xs transition flex items-center gap-1.5 shrink-0"
          >
            <BookOpen className="w-3.5 h-3.5" /><span>选用官方教材</span>
          </button>
        </div>
      )}

      <div>
        <label className="block text-xs font-semibold text-slate-500 mb-2 uppercase tracking-wider">选择学段 (STAGE)</label>
        <div className="grid grid-cols-3 gap-3">
          {[
            { id: 'primary', label: '小学 (Primary)', desc: '1~6年级，基础概念与识记' },
            { id: 'junior', label: '初中 (Junior)', desc: '7~9年级，逻辑推理与代数几何' },
            { id: 'senior', label: '高中 (Senior)', desc: '高一~高三，模块综合与深度推演' },
          ].map((stage) => (
            <button
              key={stage.id}
              type="button"
              onClick={() => onStageChange(stage.id as Stage)}
              className={`p-3 rounded-xl border text-left transition-all ${spec.stage === stage.id ? 'border-brand-600 bg-brand-50/50 ring-2 ring-brand-500/20 shadow-xs' : 'border-slate-200 hover:border-slate-300'}`}
            >
              <div className="font-bold text-sm text-slate-900">{stage.label}</div>
              <div className="text-[11px] text-slate-500 mt-0.5">{stage.desc}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">试卷标题</label>
          <input type="text" value={spec.title} onChange={(event) => setSpec({ ...spec, title: event.target.value })}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden" />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">学科与年级标签</label>
          <div className="grid grid-cols-2 gap-2">
            <select value={spec.stage_year} onChange={(event) => {
              const year = Number(event.target.value);
              setSpec({ ...spec, stage_year: year, grade_label: gradeLabelForStage(spec.stage, year),
                material_id: undefined, textbook_cover: undefined, textbook: null,
                taught_scope: { ...spec.taught_scope, scope_confirmed: false } });
            }} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800">
              {Array.from({ length: spec.stage === 'primary' ? 6 : 3 }, (_, index) => index + 1).map((year) =>
                <option key={year} value={year}>{gradeLabelForStage(spec.stage, year)}</option>)}
            </select>
            <input type="text" value={spec.subject_label} onChange={(event) => setSpec({ ...spec,
              subject_label: event.target.value, subject_code: subjectCodeFromLabel(event.target.value) || spec.subject_code })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden" />
          </div>
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">教材版本 / 模块名</label>
          <input type="text" value={spec.textbook || ''} onChange={(event) => setSpec({ ...spec, textbook: event.target.value })}
            placeholder="如：人教版九年级上册"
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden" />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">使用场景与用途</label>
          <select value={spec.purpose} onChange={(event) => setSpec({ ...spec, purpose: event.target.value as any })}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800">
            <option value="diagnosis">月度诊断 / 单元评估 (diagnosis)</option>
            <option value="practice">课堂随堂练习 (practice)</option>
            <option value="review">期末综合复习 (review)</option>
            <option value="formal">学校正式纸笔考试 (formal)</option>
          </select>
        </div>
      </div>
    </div>
  );
}

