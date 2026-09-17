import React, { useState, useEffect } from 'react';
import {
  Save,
  Eye,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  Info,
} from 'lucide-react';
import { GeneratedCandidate } from '../types/candidate';
import { ValidationRecord } from '../types/validation';
import { api } from '../lib/api';
import { MathRenderer } from '../lib/math';
import { formatScoreX100 } from '../lib/scoring';
import { makePublicProjection } from '../lib/projection';
import { StatusBadge } from '../components/StatusBadge';

interface ExamEditorProps {
  onGoToReview: () => void;
}

export const ExamEditor: React.FC<ExamEditorProps> = ({ onGoToReview }) => {
  const [candidates, setCandidates] = useState<GeneratedCandidate[]>([]);
  const [validationRecords, setValidationRecords] = useState<Record<string, ValidationRecord>>({});
  const [selectedId, setSelectedId] = useState<string>('slot_01');
  const [isStudentView, setIsStudentView] = useState<boolean>(false);
  const [activeRightTab, setActiveRightTab] = useState<'answer' | 'blind_solve' | 'evidence'>('answer');
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isRegenerating, setIsRegenerating] = useState<boolean>(false);
  const [saveToast, setSaveToast] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    const cands = await api.getCandidates();
    setCandidates(cands);
    const val = await api.getValidationRecords();
    setValidationRecords(val);
  };

  const currentCandidate = candidates.find((c) => c.public.local_id === selectedId) || candidates[0];
  const currentValidation = currentCandidate ? validationRecords[currentCandidate.public.local_id] : null;

  if (!currentCandidate) {
    return <div className="p-8 text-center text-slate-500">正在加载题目编辑工作台...</div>;
  }

  // 提取 Prompt 纯文本供编辑
  const currentPromptText = currentCandidate.public.prompt
    .map((b) => (b.type === 'text' ? b.text : b.type === 'math' ? `$${b.latex}$` : ''))
    .join(' ');

  // 更新当前题目 prompt
  const handlePromptChange = (text: string) => {
    const updated = candidates.map((c) => {
      if (c.public.local_id === currentCandidate.public.local_id) {
        return {
          ...c,
          public: {
            ...c.public,
            prompt: [{ type: 'text' as const, text }],
          },
        };
      }
      return c;
    });
    setCandidates(updated);
  };

  // 更新选项内容
  const handleOptionChange = (optId: string, text: string) => {
    const updated = candidates.map((c) => {
      if (c.public.local_id === currentCandidate.public.local_id) {
        const newOptions = c.public.options.map((opt) => {
          if (opt.id === optId) {
            return {
              ...opt,
              content: [{ type: 'text' as const, text }],
            };
          }
          return opt;
        });
        return {
          ...c,
          public: { ...c.public, options: newOptions },
        };
      }
      return c;
    });
    setCandidates(updated);
  };

  // 保存修改 (触发展示：修改后旧校验依据失效并自动变为 REVIEW)
  const handleSave = async () => {
    setIsSaving(true);
    await api.updateCandidate(currentCandidate);
    const val = await api.getValidationRecords();
    setValidationRecords(val);
    setIsSaving(false);
    setSaveToast('题面已保存！旧自动校验已失效，状态已自动转为 [待复核 REVIEW]。');
    setTimeout(() => setSaveToast(null), 4000);
  };

  // 重新生成此题
  const handleRegenerate = async () => {
    setIsRegenerating(true);
    try {
      await api.regenerateQuestion(currentCandidate.public.local_id);
      const [cands, val] = await Promise.all([
        api.getCandidates(),
        api.getValidationRecords(),
      ]);
      setCandidates(cands);
      setValidationRecords(val);
      setSaveToast('已通过 Hermes 调用 DeepSeek 完成单题重新生成与独立盲解！');
    } catch (err) {
      console.error(err);
      setSaveToast('重新生成失败，请检查后端服务与网络连接。');
    } finally {
      setIsRegenerating(false);
      setTimeout(() => setSaveToast(null), 4000);
    }
  };

  // 真实学生视图投影 (彻底剥离私有答案)
  const displayedQuestion = isStudentView
    ? makePublicProjection(currentCandidate)
    : currentCandidate.public;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-4">
      {/* Action Header Banner */}
      <div className="bg-white px-6 py-3.5 rounded-2xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-brand-100 text-brand-800">
            阶段三
          </span>
          <h1 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            三栏命题编辑工作台 (Question Workbench)
          </h1>
        </div>

        <div className="flex items-center gap-3">
          {/* Student / Teacher View Toggle */}
          <button
            onClick={() => setIsStudentView(!isStudentView)}
            className={`px-3.5 py-1.5 rounded-xl border text-xs font-bold flex items-center gap-1.5 transition ${
              isStudentView
                ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
                : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
            }`}
          >
            {isStudentView ? <ShieldCheck className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            <span>{isStudentView ? '真实学生答卷模式 (答案已剥离)' : '切换学生作答视角'}</span>
          </button>

          <button
            onClick={onGoToReview}
            className="px-4 py-1.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl flex items-center gap-1.5 shadow-sm transition"
          >
            <span>进入审核门禁</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {saveToast && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-center gap-2 animate-fadeIn">
          <Info className="w-4 h-4 text-amber-600 shrink-0" />
          <span>{saveToast}</span>
        </div>
      )}

      {/* Main 3-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* ===================== Column 1: Left Question Outline (3 cols) ===================== */}
        <div className="lg:col-span-3 bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-3 max-h-[820px] overflow-y-auto">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <span className="font-bold text-xs text-slate-700">题目目录与状态</span>
            <span className="text-[11px] text-slate-400">共 {candidates.length} 题</span>
          </div>

          <div className="space-y-1.5">
            {candidates.map((cand, idx) => {
              const val = validationRecords[cand.public.local_id];
              const isSelected = cand.public.local_id === currentCandidate.public.local_id;

              return (
                <button
                  key={cand.public.local_id}
                  onClick={() => setSelectedId(cand.public.local_id)}
                  className={`w-full p-2.5 rounded-xl border text-left transition-all flex items-center justify-between gap-2 ${
                    isSelected
                      ? 'border-brand-500 bg-brand-50/60 ring-2 ring-brand-500/20 shadow-xs'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <div className="flex items-center gap-2 overflow-hidden">
                    <span
                      className={`w-6 h-6 rounded-md flex items-center justify-center font-bold text-xs shrink-0 ${
                        isSelected ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {idx + 1}
                    </span>
                    <div className="truncate">
                      <div className="text-xs font-semibold text-slate-900 truncate">
                        {cand.public.kind === 'single_choice'
                          ? '单选'
                          : cand.public.kind === 'solution'
                          ? '解答'
                          : '填空'}
                        : {cand.public.prompt[0]?.type === 'text' ? cand.public.prompt[0].text.slice(0, 16) : '数学题'}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        {formatScoreX100(cand.public.score_x100)} 分
                      </div>
                    </div>
                  </div>

                  <StatusBadge status={val?.overall_status || 'PASS'} />
                </button>
              );
            })}
          </div>
        </div>

        {/* ===================== Column 2: Middle Workbench / Editor (5 cols) ===================== */}
        <div className="lg:col-span-5 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          {/* Middle Top: Bar */}
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm text-slate-900">
                题目 #{currentCandidate.public.local_id}
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold">
                {formatScoreX100(currentCandidate.public.score_x100)} 分
              </span>
            </div>

            {!isStudentView && (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleRegenerate}
                  disabled={isRegenerating}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 text-xs font-semibold text-slate-700 flex items-center gap-1 transition"
                  title="沿用蓝图槽位目标，重新调用 Agent 命题"
                >
                  <Sparkles className={`w-3.5 h-3.5 text-amber-500 ${isRegenerating ? 'animate-spin' : ''}`} />
                  <span>{isRegenerating ? '重构中...' : '重构此题'}</span>
                </button>

                <button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-xs font-bold text-white flex items-center gap-1 shadow-xs transition"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>{isSaving ? '保存中...' : '保存修改'}</span>
                </button>
              </div>
            )}
          </div>

          {/* Student Mode Notice */}
          {isStudentView ? (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>当前处于【真实学生端视图】：完全剥离了答案及评分属性，渲染真实卷面。</span>
            </div>
          ) : null}

          {/* Live Prompt KaTeX Preview Box */}
          <div className="p-4 bg-slate-50/80 rounded-xl border border-slate-200 space-y-2">
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
              卷面题干预览 (KaTeX LaTeX 实时渲染):
            </div>
            <div className="text-sm font-medium leading-relaxed">
              <MathRenderer content={displayedQuestion.prompt} />
            </div>
          </div>

          {/* Prompt Raw Text Editor (Hidden in student view) */}
          {!isStudentView && (
            <div className="space-y-1.5">
              <label className="block text-xs font-bold text-slate-700">
                编辑题干 (支持 $公式$ 或 $$块级公式$$):
              </label>
              <textarea
                value={currentPromptText}
                onChange={(e) => handlePromptChange(e.target.value)}
                rows={3}
                className="w-full border border-slate-300 rounded-xl p-3 text-xs text-slate-800 font-mono leading-relaxed focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
              />
            </div>
          )}

          {/* Options Editor / Preview (if choices) */}
          {currentCandidate.public.options && currentCandidate.public.options.length > 0 && (
            <div className="space-y-2.5 pt-2">
              <label className="block text-xs font-bold text-slate-700">
                选项设置 (Options):
              </label>
              <div className="space-y-2">
                {currentCandidate.public.options.map((opt) => {
                  const optText = opt.content
                    .map((b) => (b.type === 'text' ? b.text : b.type === 'math' ? `$${b.latex}$` : ''))
                    .join(' ');

                  return (
                    <div
                      key={opt.id}
                      className="p-2.5 rounded-xl border border-slate-200 bg-white flex items-center gap-3 text-xs"
                    >
                      <span className="w-6 h-6 rounded-md bg-slate-100 text-slate-800 font-bold flex items-center justify-center shrink-0">
                        {opt.label || opt.id.replace('opt_', '')}
                      </span>
                      <div className="flex-1">
                        {isStudentView ? (
                          <MathRenderer content={opt.content} />
                        ) : (
                          <input
                            type="text"
                            value={optText}
                            onChange={(e) => handleOptionChange(opt.id, e.target.value)}
                            className="w-full border-b border-transparent hover:border-slate-300 focus:border-brand-500 focus:outline-hidden py-1 px-1 text-xs"
                          />
                        )}
                      </div>
                      <div className="shrink-0 text-slate-400">
                        <MathRenderer content={opt.content} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Answer Space Setting */}
          <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-100">
            <span>预留作答空间: {currentCandidate.public.answer_space_lines} 行</span>
            <span>材料依赖: {currentCandidate.public.material_ids.length > 0 ? '材料综合' : '独立小题'}</span>
          </div>
        </div>

        {/* ===================== Column 3: Right Verification Evidence (4 cols) ===================== */}
        <div className="lg:col-span-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          {/* Tab Navigation */}
          <div className="flex rounded-xl bg-slate-100 p-1 text-xs font-medium text-slate-600">
            <button
              onClick={() => setActiveRightTab('answer')}
              className={`flex-1 py-1.5 rounded-lg transition ${
                activeRightTab === 'answer'
                  ? 'bg-white text-slate-900 font-bold shadow-xs'
                  : 'hover:text-slate-900'
              }`}
            >
              参考答案与细则
            </button>
            <button
              onClick={() => setActiveRightTab('blind_solve')}
              className={`flex-1 py-1.5 rounded-lg transition ${
                activeRightTab === 'blind_solve'
                  ? 'bg-white text-slate-900 font-bold shadow-xs'
                  : 'hover:text-slate-900'
              }`}
            >
              独立盲解对比
            </button>
            <button
              onClick={() => setActiveRightTab('evidence')}
              className={`flex-1 py-1.5 rounded-lg transition ${
                activeRightTab === 'evidence'
                  ? 'bg-white text-slate-900 font-bold shadow-xs'
                  : 'hover:text-slate-900'
              }`}
            >
              数学校验依据
            </button>
          </div>

          {/* TAB 1: Reference Answer & Rubric */}
          {activeRightTab === 'answer' && (
            <div className="space-y-4 text-xs">
              {currentCandidate.private.answers.map((ans, idx) => (
                <div key={idx} className="space-y-3">
                  <div className="p-3 bg-brand-50/70 border border-brand-200 rounded-xl space-y-1.5">
                    <span className="text-[11px] font-bold text-brand-800 block">标准参考答案:</span>
                    <span className="font-mono text-sm font-bold text-brand-900 bg-white px-2 py-0.5 rounded border border-brand-200 inline-block">
                      {ans.answer_text}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <span className="text-[11px] font-bold text-slate-700 block">详细解析过程:</span>
                    <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl leading-relaxed">
                      <MathRenderer content={ans.explanation} />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <span className="text-[11px] font-bold text-slate-700 block">按步骤给分细则 (Scoring Rubric):</span>
                    <div className="space-y-1.5">
                      {ans.scoring_rubric.map((r, sIdx) => (
                        <div
                          key={sIdx}
                          className="p-2 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between gap-2"
                        >
                          <div className="text-slate-700">
                            <span className="font-bold">第{r.step}步: </span>
                            <span>{r.criterion}</span>
                          </div>
                          <span className="px-1.5 py-0.5 bg-brand-100 text-brand-800 rounded font-bold shrink-0">
                            +{formatScoreX100(r.score_x100)}分
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* TAB 2: Blind Solver Comparison Report */}
          {activeRightTab === 'blind_solve' && currentValidation && (
            <div className="space-y-4 text-xs">
              <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-indigo-900">盲解角色 (blind-solver) 报告</span>
                  {currentValidation.blind_solve.is_same_model && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-200/80 text-indigo-900 font-mono font-bold">
                      [SAME_MODEL 标注]
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-indigo-700 leading-relaxed">
                  独立盲解进程在严格屏蔽参考答案的环境中推理作答，耗时 {currentValidation.blind_solve.duration_ms} ms。
                </div>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">盲解推导答案:</span>
                  <span className="font-mono font-bold text-slate-900">
                    {currentValidation.blind_solve.derived_answer}
                  </span>
                </div>
                <div className="flex justify-between items-center border-t border-slate-200 pt-1.5">
                  <span className="text-slate-500">与作者答案比对:</span>
                  {currentValidation.blind_solve.match_reference ? (
                    <span className="text-emerald-600 font-bold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      完全一致 (Pass)
                    </span>
                  ) : (
                    <span className="text-rose-600 font-bold flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      存在分歧 (Conflict)
                    </span>
                  )}
                </div>
              </div>

              <div className="space-y-1.5">
                <span className="text-[11px] font-bold text-slate-700 block">盲解推理链记录:</span>
                <div className="space-y-1">
                  {currentValidation.blind_solve.steps.map((st) => (
                    <div key={st.step_number} className="p-2 rounded bg-slate-50 text-[11px] text-slate-600">
                      <span className="font-semibold text-slate-800">步骤 {st.step_number}: </span>
                      {st.description}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: SymPy & Rule Verification Evidence */}
          {activeRightTab === 'evidence' && currentValidation && (
            <div className="space-y-3 text-xs">
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl space-y-1 text-emerald-900">
                <div className="font-bold flex items-center gap-1">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  可信证据校验依据
                </div>
                <div className="text-[11px] text-emerald-700">
                  基于确定性 Python 规则与 SymPy 数学符号推导，拒绝 Agent 自报。
                </div>
              </div>

              <div className="space-y-2">
                {currentValidation.rule_checks.map((r) => (
                  <div key={r.rule_id} className="p-3 rounded-xl border border-slate-200 bg-slate-50 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900">{r.name}</span>
                      <StatusBadge status={r.status} />
                    </div>
                    <p className="text-[11px] text-slate-600">{r.detail}</p>
                    {r.evidence && (
                      <div className="font-mono text-[10px] bg-slate-200/60 p-1.5 rounded text-slate-800">
                        证据: {r.evidence}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <div className="text-[10px] text-slate-400 font-mono pt-2 border-t border-slate-100">
                快照指纹: {currentValidation.content_hash}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
