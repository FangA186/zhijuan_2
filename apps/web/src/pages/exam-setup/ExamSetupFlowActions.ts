import { Dispatch, SetStateAction } from 'react';
import { ExamBlueprint, ExamSpec } from '../../types/spec';
import { api } from '../../lib/api';
import { GenerationRuntimeState } from '../../types/job';
import { reasonLabel } from '../../lib/runtimeReasons';
import { validateScoreBalance } from '../../lib/scoring';
import { sectionIssues } from '../../lib/sectionScope';
import { PendingScopeSwitch } from './ExamSetupTypes';

interface ExamSetupFlowProps {
  spec: ExamSpec | null;
  setBlueprint: Dispatch<SetStateAction<ExamBlueprint | null>>;
  setIsGeneratingBlueprint: Dispatch<SetStateAction<boolean>>;
  setScopeNotice: Dispatch<SetStateAction<string>>;
  onBlueprintConfirmed: (blueprint: ExamBlueprint) => void;
  readiness: GenerationRuntimeState | null;
  readinessChecking: boolean;
  isGeneratingBlueprint: boolean;
  pendingScopeSwitch: PendingScopeSwitch | null;
}

export function useExamSetupFlowActions({
  spec, setBlueprint, setIsGeneratingBlueprint, onBlueprintConfirmed,
  setScopeNotice, readiness, readinessChecking, isGeneratingBlueprint, pendingScopeSwitch,
}: ExamSetupFlowProps) {
  const balanceResult = spec ? validateScoreBalance(spec.sections, spec.total_score_x100) : null;
  const scoreBalance = balanceResult && { ...balanceResult, isBalanced: balanceResult.diffX100 === 0 };
  const issues = spec ? sectionIssues(spec.sections, spec.total_score_x100, spec.multiple_choice_partial_score_x100) : [];

  // Scope edits only invalidate; changing a checkbox must never bill the model.
  const generateBlueprintForSpec = async (_targetSpec: ExamSpec) => { setBlueprint(null); return null; };

  const handleGenerateBlueprint = async () => {
    if (!spec || !spec.taught_scope.scope_confirmed || issues.length || isGeneratingBlueprint) return;
    setIsGeneratingBlueprint(true);
    try {
      await api.saveExamSpec(spec);
      let job = await api.startPlanning(crypto.randomUUID());
      const deadline = Date.now() + 360000;
      while (['QUEUED', 'RUNNING'].includes(job.status) && Date.now() < deadline) {
        setScopeNotice(`规划 Agent：${job.status}，正在设计整卷。可在原始 API 页面查看返回。`);
        await new Promise(resolve => setTimeout(resolve, 1500));
        const current = await api.getPlanning();
        if (!current || current.job_id !== job.job_id) throw new Error('配置或规划任务已变化，请重新加载');
        job = current;
      }
      if (job.status !== 'COMPLETED' || !job.result) throw new Error(job.error || '规划尚未完成；请读取现有任务，不要重复提交');
      setBlueprint(job.result); setScopeNotice('规划完成，请核对后确认。');
    } catch (err) { setScopeNotice(err instanceof Error ? err.message : '规划失败'); }
    finally { setIsGeneratingBlueprint(false); }
  };

  const handleConfirm = async () => {
    if (!spec) return;
    if (!spec.taught_scope.scope_confirmed) {
      alert('请先确认本次考查范围');
      return;
    }
    if (issues.length > 0) {
      setScopeNotice(`分值与题数存在以下矛盾，请修正后再继续：\n${issues.map((message) => `· ${message}`).join('\n')}`);
      return;
    }
    setIsGeneratingBlueprint(true);
    try {
      await api.saveExamSpec(spec);
      const freshBlueprint = await api.getBlueprint();
      if (freshBlueprint.planning_source !== 'hermes_planner') throw new Error('请先运行规划 Agent 并核对蓝图');
      setBlueprint(freshBlueprint);
      const confirmed = await api.confirmBlueprint(freshBlueprint);
      onBlueprintConfirmed(confirmed);
    } catch (err: any) {
      console.error('Confirm & Generate blueprint error:', err);
      alert(err.message || '蓝图生成失败，请检查各题型分值是否配平');
    } finally {
      setIsGeneratingBlueprint(false);
    }
  };

  const confirmBlockers: { label: string; hint: string }[] = [];
  if (pendingScopeSwitch) {
    confirmBlockers.push({ label: '待处理范围失效项', hint: '请先选择「清除」或「保留适用项」完成旧范围处理并重新确认范围。' });
  } else if (spec && !spec.taught_scope.scope_confirmed) {
    confirmBlockers.push({ label: '未确认考查范围', hint: '请勾选「我已确认本次考查范围」。' });
  }
  if (readinessChecking) {
    confirmBlockers.push({ label: '正在检查生成服务', hint: '正在核对数据库、队列、Worker 与预算状态，请稍候片刻。' });
  } else if (readiness === null || readiness.versionConfirmed !== true || readiness.ready !== true) {
    if (readiness === null || readiness.reasonCodes.length === 0) {
      confirmBlockers.push({ label: '生成服务状态未确认', hint: '服务未返回可确认的就绪信息（fail-closed），不会误允许开始命题；可点击「重新检查」再试。' });
    } else {
      readiness.reasonCodes.forEach((code) => {
        confirmBlockers.push({ label: reasonLabel(code), hint: '对应组件未就绪（' + code + '），请恢复该组件后重试。' });
      });
    }
  }

  const canConfirm = Boolean(spec && !pendingScopeSwitch && spec.taught_scope.scope_confirmed &&
    readiness !== null && readiness.versionConfirmed === true && readiness.ready === true &&
    !readinessChecking && !isGeneratingBlueprint);

  return {
    balanceResult, scoreBalance, issues, generateBlueprintForSpec,
    handleGenerateBlueprint, handleConfirm, confirmBlockers, canConfirm,
  };
}
