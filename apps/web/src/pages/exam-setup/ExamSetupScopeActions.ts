import { Dispatch, SetStateAction } from 'react';
import { ExamSpec, Stage, TextbookSummary } from '../../types/spec';
import { markTopicSources, scopeSourcesOf, scopeSwitchPartition, applyScopeSwitch, ScopeSwitchMode, topicSourceContext } from '../../lib/sectionScope';
import { stageYearFromGrade, gradeLabelForStage, subjectCodeFromLabel } from '../../lib/stageYear';
import { PendingScopeSwitch } from './ExamSetupTypes';

interface ScopeActionsProps {
  spec: ExamSpec | null;
  setSpec: Dispatch<SetStateAction<ExamSpec | null>>;
  setPendingScopeSwitch: Dispatch<SetStateAction<PendingScopeSwitch | null>>;
  pendingScopeSwitch: PendingScopeSwitch | null;
  setScopeNotice: Dispatch<SetStateAction<string>>;
  topicInput: string;
  setTopicInput: Dispatch<SetStateAction<string>>;
  excludedInput: string;
  setExcludedInput: Dispatch<SetStateAction<string>>;
  generateBlueprintForSpec: (spec: ExamSpec) => Promise<unknown>;
}

export function useExamSetupScopeActions({
  spec, setSpec, setPendingScopeSwitch, pendingScopeSwitch, setScopeNotice, topicInput, setTopicInput,
  excludedInput, setExcludedInput, generateBlueprintForSpec,
}: ScopeActionsProps) {
  const scopeContext = spec ? topicSourceContext(spec.stage, spec.material_id, spec.subject_code) : null;
  const scopeSources = spec && scopeContext ? scopeSourcesOf(spec.taught_scope, scopeContext) : {};

  const beginScopeSwitch = (nextSpec: ExamSpec) => {
    if (!scopeContext) return;
    const partition = scopeSwitchPartition(nextSpec.taught_scope, scopeContext);
    setPendingScopeSwitch({
      nextSpec,
      staleTextbook: [...partition.staleTextbook, ...partition.staleTemplate],
      staleTemplate: [],
      manual: partition.manual,
    });
  };
  const handleStageChange = (newStage: Stage) => {
    if (!spec) return;
    const grade_label = gradeLabelForStage(newStage, 1);
    const subject_label = spec.subject_label.replace(/^(小学|初中|高中)/, '') || '数学';
    beginScopeSwitch({
      ...spec,
      stage: newStage,
      grade_label,
      stage_year: 1,
      subject_code: subjectCodeFromLabel(subject_label) || spec.subject_code,
      subject_label,
      material_id: undefined,
      textbook_cover: undefined,
      textbook: null,
      module: null,
      title: spec.title,
    });
  };
  const confirmScopeSwitch = (mode: ScopeSwitchMode) => {
    if (!pendingScopeSwitch || !scopeContext) return;
    const nextSpec = pendingScopeSwitch.nextSpec;
    const toContext = topicSourceContext(nextSpec.stage, nextSpec.material_id, nextSpec.subject_code);
    const applied = { ...nextSpec, taught_scope: applyScopeSwitch(nextSpec.taught_scope, mode, scopeContext, toContext) };
    setSpec(applied);
    setPendingScopeSwitch(null);
    void generateBlueprintForSpec(applied);
    setScopeNotice(mode === 'clear'
      ? '已清除随旧教材/模板带入的失效范围项，仅保留手动补充项；请重新勾选范围并确认。'
      : '保留了全部旧范围项，但旧教材章节可能不属于新学段；请逐项核对勾选并重新确认考查范围。');
  };
  const handleAddTopic = () => {
    if (!spec || !scopeContext || !topicInput.trim()) return;
    const topic = topicInput.trim();
    if (!spec.taught_scope.topics.includes(topic)) {
      markTopicSources(scopeContext, [topic], 'manual');
      const updated = {
        ...spec,
        taught_scope: { ...spec.taught_scope, scope_confirmed: false, topics: [...spec.taught_scope.topics, topic] },
      };
      setSpec(updated);
      void generateBlueprintForSpec(updated);
    }
    setTopicInput('');
  };
  const handleRemoveTopic = (topic: string) => {
    if (!spec) return;
    const updated = {
      ...spec,
      taught_scope: {
        ...spec.taught_scope, scope_confirmed: false,
        topics: spec.taught_scope.topics.filter((item) => item !== topic),
      },
    };
    setSpec(updated);
    void generateBlueprintForSpec(updated);
  };
  const handleAddExcluded = () => {
    if (!spec || !excludedInput.trim()) return;
    const topic = excludedInput.trim();
    if (!spec.taught_scope.excluded_topics.includes(topic)) {
      const updated = {
        ...spec,
        taught_scope: { ...spec.taught_scope, scope_confirmed: false, excluded_topics: [...spec.taught_scope.excluded_topics, topic] },
      };
      setSpec(updated);
      void generateBlueprintForSpec(updated);
    }
    setExcludedInput('');
  };
  const handleRemoveExcluded = (topic: string) => {
    if (!spec) return;
    const updated = {
      ...spec,
      taught_scope: {
        ...spec.taught_scope, scope_confirmed: false,
        excluded_topics: spec.taught_scope.excluded_topics.filter((item) => item !== topic),
      },
    };
    setSpec(updated);
    void generateBlueprintForSpec(updated);
  };
  const handleAddTopics = (topics: string[]) => {
    if (!spec || !scopeContext) return;
    markTopicSources(scopeContext, topics, 'textbook');
    const updated = {
      ...spec,
      taught_scope: {
        ...spec.taught_scope, scope_confirmed: false,
        topics: Array.from(new Set([...spec.taught_scope.topics, ...topics])),
      },
    };
    setSpec(updated);
    void generateBlueprintForSpec(updated);
  };
  const handleAddExcludedTopics = (topics: string[]) => {
    if (!spec) return;
    const updated = {
      ...spec,
      taught_scope: {
        ...spec.taught_scope, scope_confirmed: false,
        excluded_topics: Array.from(new Set([...spec.taught_scope.excluded_topics, ...topics])),
      },
    };
    setSpec(updated);
    void generateBlueprintForSpec(updated);
  };
  const clearTopics = () => {
    if (!spec) return;
    const updated = { ...spec, taught_scope: { ...spec.taught_scope, scope_confirmed: false, topics: [] } };
    setSpec(updated);
    void generateBlueprintForSpec(updated);
  };
  const clearExcludedTopics = () => {
    if (!spec) return;
    setSpec({ ...spec, taught_scope: { ...spec.taught_scope, scope_confirmed: false, excluded_topics: [] } });
  };
  const handleSelectTextbook = (mat: TextbookSummary) => {
    if (!spec) return;
    let newStage: Stage = spec.stage;
    const stageName = mat.dims?.zxxxd?.name || '';
    if (stageName.includes('小')) newStage = 'primary';
    else if (stageName.includes('初')) newStage = 'junior';
    else if (stageName.includes('高')) newStage = 'senior';

    const gradeName = mat.dims?.zxxnj?.name || '';
    const moduleName = mat.dims?.zxxcc?.name || '';
    const subjectName = mat.dims?.zxxxk?.name || '';
    const versionName = mat.dims?.zxxbb?.name || '';
    const stage_year = stageYearFromGrade(newStage, gradeName) ?? (newStage === spec.stage ? spec.stage_year : 1);
    const grade_label = gradeLabelForStage(newStage, stage_year);
    const subject_label = subjectName || spec.subject_label.replace(/^(小学|初中|高中)/, '');
    if (subjectName && !subjectCodeFromLabel(subjectName)) {
      alert(`暂不识别教材学科“${subjectName}”，请核对后选择`);
      return;
    }
    const subject_code = subjectCodeFromLabel(subject_label) || spec.subject_code;
    const fullTextbookName = `${versionName ? versionName + ' ' : ''}${mat.title || moduleName}`.trim();
    const suggestedTitle = `${mat.title || (grade_label + subjectName)} 阶段性学情诊断测评卷`;
    const coverUrl = mat.thumb || `/api/v1/curriculum/covers/${mat.id}.jpg`;
    const updated = {
      ...spec,
      material_id: mat.id,
      textbook_cover: coverUrl,
      stage: newStage,
      stage_year,
      grade_label,
      subject_code,
      subject_label,
      textbook: fullTextbookName,
      module: moduleName || null,
      title: !spec.title || spec.title.includes('测试卷') || spec.title.includes('诊断') ? suggestedTitle : spec.title,
    };
    if (newStage !== spec.stage || mat.id !== spec.material_id) beginScopeSwitch(updated);
    else setSpec(updated);
  };

  return {
    scopeContext, scopeSources, beginScopeSwitch, handleStageChange, confirmScopeSwitch,
    handleAddTopic, handleRemoveTopic, handleAddExcluded, handleRemoveExcluded,
    handleAddTopics, handleAddExcludedTopics, clearTopics, clearExcludedTopics, handleSelectTextbook,
  };
}
