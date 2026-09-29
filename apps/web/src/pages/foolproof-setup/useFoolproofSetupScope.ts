import { concreteTopics, alignConcreteSections } from '../../lib/topicPlanning';
import type { ExamSection, ExamSpec, Stage, TextbookSummary } from '../../types/spec';
import type { ScopeSwitchMode } from '../../lib/sectionScope';
import { applyScopeSwitch, markTopicSources, scopeSourcesOf, scopeSwitchPartition, topicSourceContext } from '../../lib/sectionScope';
import { gradeLabelForStage, stageYearFromGrade, subjectCodeFromLabel } from '../../lib/stageYear';
import { PRESET_DEFINITIONS } from './foolproofSetupPresets';
import type { LoadedFoolproofSetupState } from './useFoolproofSetupBase';

export function useFoolproofSetupScope(state: LoadedFoolproofSetupState) {
  const { spec, setSpec } = state;
  const scopeContext = topicSourceContext(spec.stage, spec.material_id, spec.subject_code);
  const scopeSources = scopeSourcesOf(spec.taught_scope, scopeContext);
  const {
    setPresetType, setTemplateApplied, customTopicInput, setCustomTopicInput,
    setPendingScopeSwitch, setScopeNotice, setPreview, setPreviewSpec,
    setIsTextbookModalOpen, pendingScopeSwitch,
  } = state;
  // 快捷切换预设类型：卡片文案与试卷数据都从 PRESET_DEFINITIONS 同一份预设计算
  const handleSelectPreset = (type: 'quiz' | 'monthly' | 'final') => {
    setPresetType(type);
    setTemplateApplied(null);
    if (!spec) return;
    const preset = PRESET_DEFINITIONS.find((p) => p.id === type);
    if (!preset) return;
    const topics = spec.taught_scope?.topics || [];
    const presetTitles: Record<string, string> = {
      quiz: `${spec.grade_label}${spec.subject_label}随堂达标小测`,
      monthly: `2026年秋季学期${spec.grade_label}${spec.subject_label}月度质量诊断评估卷`,
      final: `2026年秋季学期${spec.grade_label}${spec.subject_label}期中期末综合全真模拟卷`,
    };
    setSpec({
      ...spec,
      title: presetTitles[type],
      purpose: preset.purpose,
      duration_minutes: preset.duration_minutes,
      total_score_x100: preset.total_score_x100,
      taught_scope: { ...spec.taught_scope, scope_confirmed: false },
      sections: preset.buildSections(topics),
    });
  };

  // 快速学段切换：进入范围失效确认流程，不直接清空或静默继承旧范围
  const handleStageSelect = (stage: Stage) => {
    if (!spec || stage === spec.stage) return;
    const grade_label = gradeLabelForStage(stage, 1);
    const subject_label = spec.subject_label.replace(/^(小学|初中|高中)/, '') || '数学';
    const nextSpec: ExamSpec = {
      ...spec,
      stage,
      stage_year: 1,
      grade_label,
      subject_code: subjectCodeFromLabel(subject_label) || spec.subject_code,
      subject_label,
      material_id: undefined,
      textbook_cover: undefined,
      textbook: null,
      module: null,
      title: `2026年秋季学期${grade_label}${subject_label}阶段诊断测试卷`,
    };
    beginScopeSwitch(nextSpec);
  };

  // 切换学段/教材：列出旧范围失效项，让教师选择清除/保留适用项，并强制重新确认
  const beginScopeSwitch = (nextSpec: ExamSpec) => {
    const partition = scopeSwitchPartition(nextSpec.taught_scope, scopeContext);
    const staleTextbook = [...partition.staleTextbook, ...partition.staleTemplate];
    setPendingScopeSwitch({
      nextSpec,
      staleTextbook,
      staleTemplate: [],
      manual: partition.manual,
    });
  };

  const confirmScopeSwitch = (mode: ScopeSwitchMode) => {
    if (!pendingScopeSwitch) return;
    const { nextSpec } = pendingScopeSwitch;
    const toContext = topicSourceContext(nextSpec.stage, nextSpec.material_id, nextSpec.subject_code);
    const applied = { ...nextSpec, taught_scope: applyScopeSwitch(nextSpec.taught_scope, mode, scopeContext, toContext) };
    setSpec(applied);
    setPreview(null);
    setPreviewSpec('');
    setPendingScopeSwitch(null);
    if (mode === 'clear') {
      setScopeNotice('已清除随旧教材/模板带入的失效范围项，仅保留手动补充项；请重新勾选新教材范围并确认。');
    } else {
      setScopeNotice('保留了全部旧范围项，但旧教材章节可能不属于新学段；请逐项核对勾选并重新确认考查范围。');
    }
  };

  // 添加考点（手动补充来源）
  const handleAddTopic = () => {
    if (!customTopicInput.trim() || !spec) return;
    const t = customTopicInput.trim();
    const currentTopics = spec.taught_scope?.topics || [];
    if (!currentTopics.includes(t)) {
      markTopicSources(topicSourceContext(spec.stage, spec.material_id, spec.subject_code), [t], 'manual');
      setSpec((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          taught_scope: {
            ...prev.taught_scope,
                      scope_confirmed: false,
            topics: [...(prev.taught_scope?.topics || []), t],
          },
        };
      });
    }
    setCustomTopicInput('');
  };

  // 移除考点
  const handleRemoveTopic = (t: string) => {
    if (!spec) return;
    setSpec((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        taught_scope: {
          ...prev.taught_scope,
                      scope_confirmed: false,
          topics: (prev.taught_scope?.topics || []).filter((item) => item !== t),
        },
      };
    });
  };

  // 选用官方教材回调：学段/教材变化时先进入范围失效确认
  const handleSelectTextbook = (m: TextbookSummary) => {
    let stage: Stage = spec.stage;
    const xdName = m.dims?.zxxxd?.name || '';
    if (xdName.includes('小')) stage = 'primary';
    else if (xdName.includes('高')) stage = 'senior';

    const njName = m.dims?.zxxnj?.name || '';
    const xkName = m.dims?.zxxxk?.name || '';
    const bbName = m.dims?.zxxbb?.name || '';
    const ccName = m.dims?.zxxcc?.name || '';

    const parsedYear = stageYearFromGrade(stage, njName);
    const stageYear = parsedYear ?? (stage === spec.stage ? spec.stage_year : 1);
    const grade_label = gradeLabelForStage(stage, stageYear);
    const subject_label = xkName || spec.subject_label.replace(/^(小学|初中|高中)/, '');
    if (xkName && !subjectCodeFromLabel(xkName)) {
      alert(`暂不识别教材学科“${xkName}”，请核对后选择`);
      return;
    }
    const subject_code = subjectCodeFromLabel(subject_label) || spec.subject_code;
    const textbook = `${bbName}${njName}${ccName}`.trim() || m.title;

    const nextSpec: ExamSpec = {
      ...spec,
      stage,
      stage_year: stageYear,
      material_id: m.id,
      textbook,
      module: ccName || null,
      textbook_cover: m.thumb,
      grade_label,
      subject_label,
      subject_code,
      title: `2026年秋季学期${grade_label}${subject_label}单元质量检测卷`,
    };
    setIsTextbookModalOpen(false);
    // 更换教材（即使学段相同）都走范围失效确认：新教材章节 ≠ 旧教材章节
    beginScopeSwitch(nextSpec);
  };

  // 套用试卷模板：记录模板来源，显示"自定义模板"而非高亮预设
  const handleApplyTemplate = (template: {
    source: 'uploaded' | 'preset';
    name: string;
    title?: string;
    total_score_x100: number;
    duration_minutes: number;
    sections: ExamSection[];
  }) => {
    const newTopics = concreteTopics(Array.from(new Set(template.sections.flatMap((s) => s.topics || []))));
    // 模板建议的考点登记为 template 来源，切换教材时随失效项一起提示处理
    markTopicSources(scopeContext, newTopics, 'template');
    const merged = Array.from(new Set([...concreteTopics(spec.taught_scope?.topics || []), ...newTopics]));
    setTemplateApplied({ source: template.source, name: template.name });
    setPresetType('monthly'); // 避免预设高亮误导（卡片渲染会优先判断 templateApplied）
    setSpec({
      ...spec,
      title: template.title || spec.title,
      total_score_x100: template.total_score_x100,
      duration_minutes: template.duration_minutes,
      sections: alignConcreteSections(template.sections, merged),
      taught_scope: { ...spec.taught_scope, topics: merged, scope_confirmed: false },
    });
  };

  const isChinese = (spec.subject_label || '').includes('语文') || (spec.textbook || '').includes('语文');
  const isEnglish = (spec.subject_label || '').includes('英语') || (spec.textbook || '').includes('英语');
  return { scopeContext, scopeSources, markTopicSources, isChinese, isEnglish, handleSelectPreset,
    handleStageSelect, beginScopeSwitch, confirmScopeSwitch, handleAddTopic,
    handleRemoveTopic, handleSelectTextbook, handleApplyTemplate };
}
