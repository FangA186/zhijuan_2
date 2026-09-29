import { usePlanner } from './usePlanner';
import { repairTemplateTopicScope } from '../../lib/topicPlanning';
import { api } from '../../lib/api';
import { reasonLabel } from '../../lib/runtimeReasons';
import { sectionIssues } from '../../lib/sectionScope';
import { formatScoreX100 } from '../../lib/scoring';
import { PRESET_DEFINITIONS } from './foolproofSetupPresets';
import type { LoadedFoolproofSetupState } from './useFoolproofSetupBase';

export function useFoolproofSetupGeneration(state: LoadedFoolproofSetupState, isChinese: boolean, onStartGeneration: (spec: LoadedFoolproofSetupState['spec']) => void) {
  const { spec, setSpec, isSubmitting, setIsSubmitting, preview, setPreview, previewSpec,
    setScopeNotice, readiness, readinessChecking, hasActiveJob,
    pendingScopeSwitch, startInFlight } = state;
  const planner = usePlanner(state);
  // 先设计蓝图，确认后出题
  const handleOneClickGenerate = async () => {
    if (planner.planningBusy || isSubmitting) return;
    const repaired = repairTemplateTopicScope(spec);
    if (repaired) {
      setSpec(repaired);
      setPreview(null);
      setScopeNotice('已移除模板通用标签，并将题型对齐到已选具体考点。请核对范围、重新勾选确认，再预览计划。');
      return;
    }
    if (!spec.taught_scope.scope_confirmed) {
      alert('请先确认本次考查范围');
      return;
    }
    // 具体矛盾逐条列出（24 题配 23 条分值、负数/小数 score_x100、总分不符等），失败不清教材与已选范围
    const issues = sectionIssues(spec.sections, spec.total_score_x100, spec.multiple_choice_partial_score_x100);
    if (issues.length > 0) {
      setScopeNotice(`分值与题数存在以下矛盾，请修正后再预览：\n${issues.map((msg) => `· ${msg}`).join('\n')}`);
      return;
    }
    setIsSubmitting(true);
    try {
      const finalSpec = { ...spec };
      if (isChinese && spec.chinese_config?.poetry_list?.length) {
        const poetryTopics = spec.chinese_config.poetry_list.map((p) => `古诗文考查: ${p}`);
        if (poetryTopics.some(topic => !finalSpec.taught_scope.topics.includes(topic))) {
          setSpec({ ...finalSpec, taught_scope: {
            ...finalSpec.taught_scope,
            topics: Array.from(new Set([...finalSpec.taught_scope.topics, ...poetryTopics])),
            scope_confirmed: false,
          } });
          alert('古诗文篇目已加入考查范围，请核对并重新确认范围');
          return;
        }
        finalSpec.taught_scope = {
          ...finalSpec.taught_scope,
          topics: Array.from(new Set([...finalSpec.taught_scope.topics, ...poetryTopics])),
        };
      }
      const saved = await api.saveExamSpec(finalSpec);
      setSpec(saved);
      setPreview(null);
      await planner.beginPlanning(saved);
      setScopeNotice('');
    } catch (err: any) {
      console.error('出卷生成启动异常:', err);
      const msg = err?.message || '保存出卷设置失败，请稍后重试';
      alert(`出卷准备失败：${msg}`);
      setIsSubmitting(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmAndStart = async () => {
    if (!preview || planner.planningBusy || JSON.stringify(spec) !== previewSpec || startInFlight.current) return;
    startInFlight.current = true;
    setIsSubmitting(true);
    let confirmed = false;
    let resultUnknown = false;
    let confirmedRevision: number | null = null;
    try {
      const confirmedBlueprint = await api.confirmBlueprint(preview);
      confirmedRevision = confirmedBlueprint.revision;
      confirmed = true;
      await api.startGenerationJob('current');
      onStartGeneration(spec);
    } catch (err: any) {
      if (confirmed) {
        try {
          const job = await api.getCurrentJob('current');
          if (job && job.revision === confirmedRevision) {
            onStartGeneration(spec);
            return;
          }
        } catch {
          resultUnknown = true;
        }
      }
      alert(resultUnknown ? '启动结果未知，请刷新页面读取任务状态后再操作' : `启动出卷失败：${err?.message || '请检查计划与当前规格是否一致'}`);
    } finally {
      startInFlight.current = resultUnknown;
      setIsSubmitting(false);
    }
  };

  const confirmBlockers: { label: string; hint: string }[] = [];
  const freshReady = readiness?.versionConfirmed === true;
  if (planner.planningBusy) confirmBlockers.push({ label: '规划尚未结束', hint: '等待规划完成或对账后再确认命题。' });
  if (hasActiveJob) {
    confirmBlockers.push({ label: '已有活动生成任务', hint: '当前已有任务在运行，请先到进度页查看结果，不要重复发起命题。' });
  }
  if (pendingScopeSwitch) {
    confirmBlockers.push({ label: '待处理范围失效项', hint: '请先在上方选择「清除」或「保留适用项」完成旧范围处理并重新确认范围。' });
  } else if (!spec.taught_scope.scope_confirmed) {
    confirmBlockers.push({ label: '未确认考查范围', hint: '请勾选「我已确认本次考查范围」，再预览题槽计划。' });
  }
  if (!preview || JSON.stringify(spec) !== previewSpec) {
    confirmBlockers.push({ label: '题槽计划未生成或已过期', hint: '配置变更后需点击「让规划 Agent 设计蓝图」重新规划，确认按钮只对最新计划生效。' });
  }
  if (readinessChecking) {
    confirmBlockers.push({ label: '正在检查生成服务', hint: '正在核对数据库、队列、Worker 与预算状态，请稍候片刻。' });
  } else if (!freshReady || readiness === null || readiness.ready !== true) {
    if (readiness === null || readiness.reasonCodes.length === 0) {
      confirmBlockers.push({
        label: '生成服务状态未确认',
        hint: '服务未返回可确认的就绪信息（fail-closed），不会误允许开始命题；可点击「重新检查」再试。',
      });
    } else {
      readiness.reasonCodes.forEach((code) => {
        confirmBlockers.push({ label: reasonLabel(code), hint: '对应组件未就绪（' + code + '），请恢复该组件后重试。' });
      });
    }
  }

  const canStart =
    !planner.planningBusy && !hasActiveJob && !pendingScopeSwitch && spec.taught_scope.scope_confirmed &&
    !!preview && JSON.stringify(spec) === previewSpec &&
    !readinessChecking && readiness !== null && readiness.ready === true &&
    !isSubmitting && !startInFlight.current;

  const computePresetSummary = (preset: typeof PRESET_DEFINITIONS[number], topicCount: number) => {
    const sections = preset.buildSections(Array.from({ length: topicCount }, (_, i) => `考点${i}`));
    const count = sections.reduce((acc, s) => acc + s.count, 0);
    const total = preset.total_score_x100;
    return `${preset.duration_minutes}分钟 · ${count}题 · 满分${formatScoreX100(total)}分`;
  };


  const totalQuestions = spec.sections.reduce((acc, section) => acc + section.count, 0);
  const totalScore = (spec.total_score_x100 / 100).toFixed(0);
  const issuesList = sectionIssues(spec.sections, spec.total_score_x100, spec.multiple_choice_partial_score_x100);
  return { ...planner, handleOneClickGenerate, handleConfirmAndStart, confirmBlockers, canStart,
    computePresetSummary, totalQuestions, totalScore, issuesList };
}
