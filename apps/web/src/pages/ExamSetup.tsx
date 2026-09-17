import React, { useState, useEffect } from 'react';
import { Sparkles, Plus, Trash2, CheckCircle, AlertCircle, Edit3, ArrowRight, BookOpen } from 'lucide-react';
import { ExamSpec, Stage, ExamBlueprint, BlueprintSlot, QuestionKind, ExamSection, TextbookSummary } from '../types/spec';
import { api } from '../lib/api';
import { formatScoreX100, parseScoreToX100, validateScoreBalance } from '../lib/scoring';
import { SlotEditorModal } from '../components/SlotEditorModal';
import { TextbookSelectModal } from '../components/TextbookSelectModal';
import { ChapterTreeScopeSelector } from '../components/ChapterTreeScopeSelector';

interface ExamSetupProps {
  onBlueprintConfirmed: (blueprint: ExamBlueprint) => void;
}

export const ExamSetup: React.FC<ExamSetupProps> = ({ onBlueprintConfirmed }) => {
  const [spec, setSpec] = useState<ExamSpec | null>(null);
  const [blueprint, setBlueprint] = useState<ExamBlueprint | null>(null);
  const [editingSlot, setEditingSlot] = useState<BlueprintSlot | null>(null);
  const [isGeneratingBlueprint, setIsGeneratingBlueprint] = useState(false);
  const [topicInput, setTopicInput] = useState('');
  const [excludedInput, setExcludedInput] = useState('');
  const [isTextbookModalOpen, setIsTextbookModalOpen] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    const s = await api.getExamSpec();
    setSpec(s);
    const bp = await api.getBlueprint();
    setBlueprint(bp);
  };

  if (!spec) return <div className="p-8 text-center text-slate-500">正在读取规格配置...</div>;

  const scoreBalance = validateScoreBalance(spec.sections, spec.total_score_x100);

  // 学段切换联动
  const handleStageChange = (newStage: Stage) => {
    let grade_label = '七年级';
    let stage_year = 7;
    let subject_code = 'MATH_JUNIOR';
    let subject_label = '初中数学';

    if (newStage === 'primary') {
      grade_label = '五年级';
      stage_year = 5;
      subject_code = 'CHINESE_PRIMARY';
      subject_label = '小学语文';
    } else if (newStage === 'senior') {
      grade_label = '高一';
      stage_year = 10;
      subject_code = 'PHYSICS_SENIOR';
      subject_label = '高中物理';
    }

    setSpec({
      ...spec,
      stage: newStage,
      grade_label,
      stage_year,
      subject_code,
      subject_label,
    });
  };

  const handleAddTopic = () => {
    if (!topicInput.trim()) return;
    if (!spec.taught_scope.topics.includes(topicInput.trim())) {
      setSpec({
        ...spec,
        taught_scope: {
          ...spec.taught_scope,
          topics: [...spec.taught_scope.topics, topicInput.trim()],
        },
      });
    }
    setTopicInput('');
  };

  const handleRemoveTopic = (t: string) => {
    setSpec({
      ...spec,
      taught_scope: {
        ...spec.taught_scope,
        topics: spec.taught_scope.topics.filter((item) => item !== t),
      },
    });
  };

  const handleAddExcluded = () => {
    if (!excludedInput.trim()) return;
    if (!spec.taught_scope.excluded_topics.includes(excludedInput.trim())) {
      setSpec({
        ...spec,
        taught_scope: {
          ...spec.taught_scope,
          excluded_topics: [...spec.taught_scope.excluded_topics, excludedInput.trim()],
        },
      });
    }
    setExcludedInput('');
  };

  const handleRemoveExcluded = (t: string) => {
    setSpec({
      ...spec,
      taught_scope: {
        ...spec.taught_scope,
        excluded_topics: spec.taught_scope.excluded_topics.filter((item) => item !== t),
      },
    });
  };

  // 官方教材选取联动
  const handleSelectTextbook = (mat: TextbookSummary) => {
    let newStage: Stage = spec.stage;
    const xdName = mat.dims?.zxxxd?.name || '';
    if (xdName.includes('小')) newStage = 'primary';
    else if (xdName.includes('初')) newStage = 'junior';
    else if (xdName.includes('高')) newStage = 'senior';

    const njName = mat.dims?.zxxnj?.name || '';
    const ccName = mat.dims?.zxxcc?.name || '';
    const xkName = mat.dims?.zxxxk?.name || '';
    const bbName = mat.dims?.zxxbb?.name || '';

    let grade_label = njName || ccName || (newStage === 'senior' ? '高中' : '初中');
    let stage_year = spec.stage_year;

    if (njName.includes('一') || njName.includes('1')) stage_year = newStage === 'junior' ? 7 : newStage === 'senior' ? 10 : 1;
    else if (njName.includes('二') || njName.includes('2')) stage_year = newStage === 'junior' ? 8 : newStage === 'senior' ? 11 : 2;
    else if (njName.includes('三') || njName.includes('3')) stage_year = newStage === 'junior' ? 9 : newStage === 'senior' ? 12 : 3;
    else if (njName.includes('四') || njName.includes('4')) stage_year = 4;
    else if (njName.includes('五') || njName.includes('5')) stage_year = 5;
    else if (njName.includes('六') || njName.includes('6')) stage_year = 6;
    else if (newStage === 'senior') {
      if (ccName.includes('必修第一册') || ccName.includes('必修一') || ccName.includes('必修1')) stage_year = 10;
      else if (ccName.includes('必修第二册') || ccName.includes('必修二') || ccName.includes('必修2')) stage_year = 10;
      else if (ccName.includes('选择性必修第一册') || ccName.includes('选修一')) stage_year = 11;
      else if (ccName.includes('选择性必修第二册') || ccName.includes('选修二')) stage_year = 11;
      else if (ccName.includes('选择性必修第三册') || ccName.includes('选修三')) stage_year = 12;
      else stage_year = 10;
    }

    const subject_label = `${xdName || (newStage === 'senior' ? '高中' : newStage === 'junior' ? '初中' : '小学')}${xkName}`;
    const xkMap: Record<string, string> = {
      语文: 'CHINESE',
      数学: 'MATH',
      英语: 'ENGLISH',
      物理: 'PHYSICS',
      化学: 'CHEMISTRY',
      生物学: 'BIOLOGY',
      生物: 'BIOLOGY',
      历史: 'HISTORY',
      地理: 'GEOGRAPHY',
      道德与法治: 'MORAL',
      思想政治: 'POLITICS',
      科学: 'SCIENCE',
    };
    const codePrefix = xkMap[xkName] || 'GENERAL';
    const subject_code = `${codePrefix}_${newStage.toUpperCase()}`;

    const fullTextbookName = `${bbName ? bbName + ' ' : ''}${mat.title || ccName}`.trim();
    const suggestedTitle = `${mat.title || (grade_label + xkName)} 阶段性学情诊断测评卷`;
    const coverUrl = mat.thumb || `/api/v1/curriculum/covers/${mat.id}.jpg`;

    setSpec({
      ...spec,
      material_id: mat.id,
      textbook_cover: coverUrl,
      stage: newStage,
      stage_year,
      grade_label,
      subject_code,
      subject_label,
      textbook: fullTextbookName,
      module: ccName || null,
      title: !spec.title || spec.title.includes('测试卷') || spec.title.includes('诊断') ? suggestedTitle : spec.title,
    });
  };

  // 生成/规划蓝图槽位
  const handleGenerateBlueprint = () => {
    setIsGeneratingBlueprint(true);
    setTimeout(() => {
      let order = 1;
      const slots: BlueprintSlot[] = [];
      const availableTopics = spec.taught_scope.topics.length > 0 ? spec.taught_scope.topics : [];

      spec.sections.forEach((sec) => {
        for (let i = 0; i < sec.count; i++) {
          const fallbackTopic = sec.topics[i % sec.topics.length] || '基础核心概念';
          const target_topic = availableTopics.length > 0
            ? availableTopics[(order - 1) % availableTopics.length]
            : fallbackTopic;

          slots.push({
            slot_id: `slot_${order < 10 ? '0' + order : order}`,
            order,
            section_id: sec.id,
            kind: sec.question_type,
            target_topic,
            cognitive_target: i === 0 ? '基础理解' : i === 1 ? '运算求解' : '综合推演',
            estimated_difficulty: i === 0 ? 'basic' : i === sec.count - 1 ? 'advanced' : 'medium',
            score_x100: sec.score_each_x100,
            answer_space_lines: sec.question_type === 'solution' ? 8 : 2,
            material_id: spec.material_id,
            status: 'PENDING',
          });
          order++;
        }
      });

      const newBp: ExamBlueprint = {
        exam_id: 'exam_demo_01',
        plan_id: `plan_${Date.now()}`,
        revision: (blueprint?.revision || 0) + 1,
        confirmed: false,
        slots,
        total_score_x100: spec.total_score_x100,
        created_at: new Date().toISOString(),
      };
      setBlueprint(newBp);
      setIsGeneratingBlueprint(false);
    }, 800);
  };

  // 确认蓝图
  const handleConfirm = async () => {
    if (!blueprint) return;
    const confirmed = await api.confirmBlueprint(blueprint);
    onBlueprintConfirmed(confirmed);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Page Title & Scope Reminder */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-brand-100 text-brand-800">
              阶段一
            </span>
            <h1 className="text-xl font-bold text-slate-900">命题规格定义与蓝图规划 (ExamSpec & Blueprint)</h1>
          </div>
          <p className="text-sm text-slate-500">
            按教学范围、知识点及考查目标组织，模型调用前严格执行总分矛盾拦截与分值配平。
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleGenerateBlueprint}
            disabled={isGeneratingBlueprint || !scoreBalance.isBalanced}
            className="px-4 py-2.5 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-300 text-white font-bold text-sm rounded-xl flex items-center gap-2 shadow-xs transition"
          >
            <Sparkles className="w-4 h-4 text-amber-300" />
            {isGeneratingBlueprint ? '正在规划槽位...' : '重新生成蓝图槽位'}
          </button>
          {blueprint && (
            <button
              onClick={handleConfirm}
              className="px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-sm rounded-xl flex items-center gap-2 shadow-sm transition"
            >
              <span>确认蓝图并开始命题</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: Exam Spec Editor */}
        <div className="lg:col-span-2 space-y-6">
          {/* Card 1: 基础信息与教材体系联动 */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-brand-500"></span>
                1. 基础信息与教材选用 (国家智慧教育平台标准)
              </h2>
              <button
                type="button"
                onClick={() => setIsTextbookModalOpen(true)}
                className="px-3 py-1.5 bg-brand-50 hover:bg-brand-100 text-brand-700 font-semibold text-xs rounded-xl border border-brand-200 transition flex items-center gap-1.5 shadow-2xs"
              >
                <BookOpen className="w-3.5 h-3.5 text-brand-600" />
                <span>{spec.material_id ? '更换教材' : '切换/选用教材'}</span>
              </button>
            </div>

            {/* 教材绑定状态卡片 */}
            {spec.material_id ? (
              <div className="p-4 rounded-xl border border-brand-200 bg-gradient-to-r from-brand-50/70 via-indigo-50/40 to-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-3.5">
                  {spec.textbook_cover ? (
                    <img
                      src={spec.textbook_cover}
                      alt="教材封面"
                      className="w-12 h-16 object-cover rounded-lg shadow-xs border border-slate-200 shrink-0 bg-white"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                  ) : (
                    <div className="w-12 h-16 rounded-lg bg-brand-100 text-brand-700 flex flex-col items-center justify-center font-bold text-xs shrink-0 border border-brand-200">
                      <BookOpen className="w-5 h-5 mb-1" />
                      <span>教材</span>
                    </div>
                  )}
                  <div>
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-brand-600 text-white shadow-2xs">
                        国家智慧教育平台教材
                      </span>
                      <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800">
                        章节大纲已联动
                      </span>
                    </div>
                    <div className="font-bold text-slate-900 text-sm">{spec.textbook || spec.title}</div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {spec.subject_label} · {spec.grade_label} · {spec.curriculum_system}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => setIsTextbookModalOpen(true)}
                    className="px-3 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 font-semibold text-xs rounded-xl shadow-2xs transition flex items-center gap-1.5"
                  >
                    <BookOpen className="w-3.5 h-3.5 text-brand-600" />
                    <span>更换教材</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-4 rounded-xl border border-dashed border-slate-300 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center shrink-0">
                    <BookOpen className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="font-bold text-sm text-slate-800">快速从国家中小学智慧教育平台选用教材</div>
                    <div className="text-xs text-slate-500">
                      同步 3,200+ 本官方教材目录大纲，自动填充学段学科，并在下方一键勾选章节出题。
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setIsTextbookModalOpen(true)}
                  className="px-3.5 py-2 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-xs transition flex items-center gap-1.5 shrink-0"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  <span>选用官方教材</span>
                </button>
              </div>
            )}

            {/* Stage Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-2 uppercase tracking-wider">
                选择学段 (STAGE)
              </label>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { id: 'primary', label: '小学 (Primary)', desc: '1~6年级，基础概念与识记' },
                  { id: 'junior', label: '初中 (Junior)', desc: '7~9年级，逻辑推理与代数几何' },
                  { id: 'senior', label: '高中 (Senior)', desc: '高一~高三，模块综合与深度推演' },
                ].map((stg) => (
                  <button
                    key={stg.id}
                    type="button"
                    onClick={() => handleStageChange(stg.id as Stage)}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      spec.stage === stg.id
                        ? 'border-brand-600 bg-brand-50/50 ring-2 ring-brand-500/20 shadow-xs'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className="font-bold text-sm text-slate-900">{stg.label}</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">{stg.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">试卷标题</label>
                <input
                  type="text"
                  value={spec.title}
                  onChange={(e) => setSpec({ ...spec, title: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">学科与年级标签</label>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    value={spec.grade_label}
                    onChange={(e) => setSpec({ ...spec, grade_label: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
                  />
                  <input
                    type="text"
                    value={spec.subject_label}
                    onChange={(e) => setSpec({ ...spec, subject_label: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">教材版本 / 模块名</label>
                <input
                  type="text"
                  value={spec.textbook || ''}
                  onChange={(e) => setSpec({ ...spec, textbook: e.target.value })}
                  placeholder="如：人教版九年级上册"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">使用场景与用途</label>
                <select
                  value={spec.purpose}
                  onChange={(e) => setSpec({ ...spec, purpose: e.target.value as any })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
                >
                  <option value="diagnosis">月度诊断 / 单元评估 (diagnosis)</option>
                  <option value="practice">课堂随堂练习 (practice)</option>
                  <option value="review">期末综合复习 (review)</option>
                  <option value="formal">学校正式纸笔考试 (formal)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Card 2: 考查范围与超纲排除 */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-brand-500"></span>
                2. 教学考查知识点与排除约束 (Taught Scope)
              </h2>
              {spec.material_id && (
                <span className="text-xs text-slate-500 hidden sm:inline">
                  当前教材: <span className="font-semibold text-brand-700">{spec.textbook}</span>
                </span>
              )}
            </div>

            {/* 嵌入国家中小学平台教材章节大纲选择器 */}
            <ChapterTreeScopeSelector
              materialId={spec.material_id}
              textbookTitle={spec.textbook || spec.title}
              existingTopics={spec.taught_scope.topics}
              existingExcluded={spec.taught_scope.excluded_topics}
              onAddTopics={(newTopics) => {
                const merged = Array.from(new Set([...spec.taught_scope.topics, ...newTopics]));
                setSpec({
                  ...spec,
                  taught_scope: {
                    ...spec.taught_scope,
                    topics: merged,
                  },
                });
              }}
              onAddExcludedTopics={(newExcluded) => {
                const merged = Array.from(new Set([...spec.taught_scope.excluded_topics, ...newExcluded]));
                setSpec({
                  ...spec,
                  taught_scope: {
                    ...spec.taught_scope,
                    excluded_topics: merged,
                  },
                });
              }}
            />

            {/* Included Topics */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-slate-600">
                  本次考查知识点（命题目标，共 <strong className="text-emerald-700">{spec.taught_scope.topics.length}</strong> 项）:
                </label>
                {spec.taught_scope.topics.length > 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      setSpec({
                        ...spec,
                        taught_scope: {
                          ...spec.taught_scope,
                          topics: [],
                        },
                      });
                    }}
                    className="text-[11px] text-slate-400 hover:text-rose-600 transition"
                  >
                    清空考查点
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-2 mb-2">
                {spec.taught_scope.topics.length === 0 ? (
                  <span className="text-xs text-slate-400 italic py-1">暂无知识点，请从上方章节树勾选导入或在下方手动输入添加</span>
                ) : (
                  spec.taught_scope.topics.map((t) => (
                    <span
                      key={t}
                      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-2xs"
                    >
                      <span>{t}</span>
                      <button
                        onClick={() => handleRemoveTopic(t)}
                        className="text-emerald-500 hover:text-emerald-800 text-sm font-bold"
                      >
                        &times;
                      </button>
                    </span>
                  ))
                )}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={topicInput}
                  onChange={(e) => setTopicInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTopic())}
                  placeholder="手动输入知识点后按回车或点击添加..."
                  className="flex-1 border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
                />
                <button
                  type="button"
                  onClick={handleAddTopic}
                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold"
                >
                  添加知识点
                </button>
              </div>
            </div>

            {/* Excluded Topics */}
            <div className="pt-3 border-t border-slate-100">
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-slate-600">
                  严禁超纲排除内容（违禁拦截，共 <strong className="text-rose-700">{spec.taught_scope.excluded_topics.length}</strong> 项）:
                </label>
                {spec.taught_scope.excluded_topics.length > 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      setSpec({
                        ...spec,
                        taught_scope: {
                          ...spec.taught_scope,
                          excluded_topics: [],
                        },
                      });
                    }}
                    className="text-[11px] text-slate-400 hover:text-rose-600 transition"
                  >
                    清空排除项
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-2 mb-2">
                {spec.taught_scope.excluded_topics.length === 0 ? (
                  <span className="text-xs text-slate-400 italic py-1">未设排除项（命题模型将默认在考查知识点范围内生成）</span>
                ) : (
                  spec.taught_scope.excluded_topics.map((t) => (
                    <span
                      key={t}
                      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-rose-50 text-rose-800 border border-rose-200 shadow-2xs"
                    >
                      <span>{t}</span>
                      <button
                        onClick={() => handleRemoveExcluded(t)}
                        className="text-rose-500 hover:text-rose-800 text-sm font-bold"
                      >
                        &times;
                      </button>
                    </span>
                  ))
                )}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={excludedInput}
                  onChange={(e) => setExcludedInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddExcluded())}
                  placeholder="输入禁止出现的概念/公式..."
                  className="flex-1 border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-800 focus:ring-2 focus:ring-rose-500 focus:outline-hidden"
                />
                <button
                  type="button"
                  onClick={handleAddExcluded}
                  className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold"
                >
                  添加排除项
                </button>
              </div>
            </div>
          </div>

          {/* Card 3: 题型大纲与分值结构 */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-brand-500"></span>
                3. 大题题型与分值配平 (Sections)
              </h2>
              <button
                type="button"
                onClick={() => {
                  const newSec: ExamSection = {
                    id: `sec_${Date.now()}`,
                    title: `新增大题题组`,
                    question_type: 'short_answer',
                    count: 2,
                    score_each_x100: 500,
                    topics: ['核心考查点'],
                  };
                  setSpec({ ...spec, sections: [...spec.sections, newSec] });
                }}
                className="px-3 py-1 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg flex items-center gap-1"
              >
                <Plus className="w-3.5 h-3.5" />
                添加题型大组
              </button>
            </div>

            <div className="space-y-3">
              {spec.sections.map((sec, idx) => (
                <div
                  key={sec.id}
                  className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <input
                      type="text"
                      value={sec.title}
                      onChange={(e) => {
                        const updated = [...spec.sections];
                        updated[idx].title = e.target.value;
                        setSpec({ ...spec, sections: updated });
                      }}
                      className="font-bold text-sm bg-transparent border-b border-transparent hover:border-slate-300 focus:border-brand-500 focus:bg-white focus:outline-hidden px-1 py-0.5 flex-1"
                    />
                    <button
                      onClick={() => {
                        const updated = spec.sections.filter((_, i) => i !== idx);
                        setSpec({ ...spec, sections: updated });
                      }}
                      className="text-slate-400 hover:text-rose-600 p-1"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="grid grid-cols-3 gap-3 text-xs">
                    <div>
                      <label className="text-slate-500 mb-1 block">题型</label>
                      <select
                        value={sec.question_type}
                        onChange={(e) => {
                          const updated = [...spec.sections];
                          updated[idx].question_type = e.target.value as QuestionKind;
                          setSpec({ ...spec, sections: updated });
                        }}
                        className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5"
                      >
                        <option value="single_choice">单项选择题</option>
                        <option value="multiple_choice">多项选择题</option>
                        <option value="true_false">判断题</option>
                        <option value="fill_blank">填空题</option>
                        <option value="solution">计算解答题</option>
                        <option value="short_answer">简答题</option>
                        <option value="essay">作文/论述题</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-slate-500 mb-1 block">题量 (道)</label>
                      <input
                        type="number"
                        min="1"
                        max="50"
                        value={sec.count}
                        onChange={(e) => {
                          const updated = [...spec.sections];
                          updated[idx].count = parseInt(e.target.value) || 1;
                          setSpec({ ...spec, sections: updated });
                        }}
                        className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5"
                      />
                    </div>

                    <div>
                      <label className="text-slate-500 mb-1 block">每题分值 (分)</label>
                      <input
                        type="number"
                        step="0.5"
                        min="1"
                        value={formatScoreX100(sec.score_each_x100)}
                        onChange={(e) => {
                          const updated = [...spec.sections];
                          updated[idx].score_each_x100 = parseScoreToX100(e.target.value);
                          setSpec({ ...spec, sections: updated });
                        }}
                        className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Col: Score Balance & Blueprint Slots Summary */}
        <div className="space-y-6">
          {/* Card: 分值实时平衡检验 */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <h3 className="text-base font-bold text-slate-900">卷面分值平衡校验器</h3>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3 text-sm">
              <div className="flex justify-between items-center">
                <span className="text-slate-500">目标满分:</span>
                <span className="font-bold text-slate-900 text-lg">
                  {formatScoreX100(spec.total_score_x100)} 分
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">当前各题合计:</span>
                <span className="font-bold text-slate-900 text-lg">
                  {formatScoreX100(scoreBalance.actualTotalX100)} 分
                </span>
              </div>
              <div className="border-t border-slate-200 pt-2 flex items-center justify-between">
                <span className="text-xs text-slate-500">配平结果:</span>
                {scoreBalance.isBalanced ? (
                  <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                    <CheckCircle className="w-3.5 h-3.5" />
                    完全平衡 (0 误差)
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs font-bold text-rose-700 bg-rose-100 px-2 py-0.5 rounded-full">
                    <AlertCircle className="w-3.5 h-3.5" />
                    相差 {formatScoreX100(Math.abs(scoreBalance.diffX100))} 分
                  </span>
                )}
              </div>
            </div>

            {!scoreBalance.isBalanced && (
              <p className="text-xs text-rose-600 leading-relaxed">
                * 注意：总分矛盾将在调用任何模型前被直接拦截。请调整题量或单题分值以配平。
              </p>
            )}
          </div>

          {/* Card: 蓝图槽位 (Slots) 规划预览 */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900">
                AI 规划槽位表 ({blueprint?.slots.length || 0} 题)
              </h3>
              <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded font-mono">
                Rev #{blueprint?.revision || 1}
              </span>
            </div>

            <div className="max-h-[420px] overflow-y-auto space-y-2 pr-1">
              {blueprint?.slots.map((slot) => (
                <div
                  key={slot.slot_id}
                  className="p-3 rounded-xl border border-slate-200 hover:border-brand-400 bg-white transition flex items-center justify-between gap-3 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-slate-100 text-slate-700 flex items-center justify-center font-bold text-[11px] shrink-0">
                      {slot.order}
                    </span>
                    <div>
                      <div className="font-semibold text-slate-900">{slot.target_topic}</div>
                      <div className="text-slate-400 text-[11px]">{slot.cognitive_target}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold text-[11px]">
                      {formatScoreX100(slot.score_x100)}分
                    </span>
                    <button
                      onClick={() => setEditingSlot(slot)}
                      className="p-1 text-slate-400 hover:text-brand-600 rounded transition"
                      title="微调此槽位"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Modal: Slot Editor */}
      <SlotEditorModal
        slot={editingSlot}
        onClose={() => setEditingSlot(null)}
        onSave={(updated) => {
          if (!blueprint) return;
          const slots = blueprint.slots.map((s) => (s.slot_id === updated.slot_id ? updated : s));
          setBlueprint({ ...blueprint, slots });
        }}
      />

      {/* Modal: Textbook Selector (National SmartEdu Platform) */}
      <TextbookSelectModal
        isOpen={isTextbookModalOpen}
        onClose={() => setIsTextbookModalOpen(false)}
        onSelect={handleSelectTextbook}
        currentMaterialId={spec.material_id}
        initialStage={spec.stage}
      />
    </div>
  );
};
