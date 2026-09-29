import { useEffect, useRef, useState } from 'react';
import type { ExamSpec, Stage, ExamBlueprint } from '../../types/spec';
import type { GenerationJob, GenerationRuntimeState } from '../../types/job';
import { api } from '../../lib/api';
import { subjectCodeFromLabel } from '../../lib/stageYear';

export function useFoolproofSetupBase() {
  const [spec, setSpec] = useState<ExamSpec | null>(null);
  const [isTextbookModalOpen, setIsTextbookModalOpen] = useState(false);
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false);
  const [presetType, setPresetType] = useState<'quiz' | 'monthly' | 'final'>('monthly');
  // 从模板弹窗套用的模板来源：上传=自定义模板、预设=精选模板名；非空时不再高亮预设卡片
  const [templateApplied, setTemplateApplied] = useState<{ source: 'uploaded' | 'preset'; name: string } | null>(null);
  const [customTopicInput, setCustomTopicInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [preview, setPreview] = useState<ExamBlueprint | null>(null);
  const [previewSpec, setPreviewSpec] = useState('');
  const [scopeNotice, setScopeNotice] = useState('');
  const [readiness, setReadiness] = useState<GenerationRuntimeState | null>(null);
  const [readinessChecking, setReadinessChecking] = useState(true);
  const [hasActiveJob, setHasActiveJob] = useState(false);
  // 切换学段/教材后的旧范围失效处理：pending 时列出失效项，等教师选择清除/保留
  const [pendingScopeSwitch, setPendingScopeSwitch] = useState<{
    nextSpec: ExamSpec;
    staleTextbook: string[];
    staleTemplate: string[];
    manual: string[];
  } | null>(null);
  const startInFlight = useRef(false);

  useEffect(() => {
    loadSpec();
  }, []);

  // C6：轮询真实就绪状态；草稿编辑不受就绪轮询影响
  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      setReadinessChecking(true);
      const state = await api.fetchGenerationReadiness();
      if (!cancelled) {
        setReadiness(state);
        setReadinessChecking(false);
      }
    };
    check();
    const timer = window.setInterval(check, 15000);
    return () => { cancelled = true; clearInterval(timer); };
  }, []);

  // 已有活动任务：只把正在推进中的 job 视为“活动”，终态（COMPLETED / PARTIAL_FAILED
  // / CANCELLED / FAILED）已归档且允许同规格重跑，不得永久禁用「确认计划并开始命题」。
  // 后端 get_current_job 对任意状态（含终态）都返回，所以这里按状态过滤。
  const ACTIVE_JOB_STATUSES: GenerationJob['status'][] = ['QUEUED', 'RUNNING', 'PAUSED', 'RECONCILING'];
  useEffect(() => {
    (async () => {
      try {
        const job = await api.getCurrentJob('current');
        setHasActiveJob(Boolean(job && ACTIVE_JOB_STATUSES.includes(job.status)));
      } catch { /* 读取失败按无任务处理 */ }
    })();
  }, []);

  const loadSpec = async () => {
    const s = await api.getExamSpec();
    const stage: Stage = s.stage || 'junior';
    const normalized: ExamSpec = {
      ...s,
      multiple_choice_partial_score_x100: s.multiple_choice_partial_score_x100 ?? 0,
      stage,
      subject_code: subjectCodeFromLabel(s.subject_label || '') || s.subject_code,
      grade_label: s.grade_label || (stage === 'senior' ? '高一' : stage === 'primary' ? '五年级' : '九年级'),
      subject_label: s.subject_label || (stage === 'senior' ? '高中数学' : stage === 'primary' ? '小学数学' : '初中数学'),
      taught_scope: {
        topics: Array.isArray(s.taught_scope?.topics) ? s.taught_scope.topics : [],
        excluded_topics: Array.isArray(s.taught_scope?.excluded_topics) ? s.taught_scope.excluded_topics : [],
        permitted_methods: Array.isArray(s.taught_scope?.permitted_methods) ? s.taught_scope.permitted_methods : [],
        scope_confirmed: s.taught_scope?.scope_confirmed === true,
      },
      sections: Array.isArray(s.sections) ? s.sections : [],
    };
    setSpec(current => current ?? normalized);
  };

  return {
    spec, setSpec, isTextbookModalOpen, setIsTextbookModalOpen,
    isTemplateModalOpen, setIsTemplateModalOpen, presetType, setPresetType,
    templateApplied, setTemplateApplied, customTopicInput, setCustomTopicInput,
    isSubmitting, setIsSubmitting, preview, setPreview, previewSpec, setPreviewSpec,
    scopeNotice, setScopeNotice, readiness, setReadiness, readinessChecking,
    setReadinessChecking, hasActiveJob, setHasActiveJob, pendingScopeSwitch,
    setPendingScopeSwitch, startInFlight,
  };
}

export type LoadedFoolproofSetupState = Omit<ReturnType<typeof useFoolproofSetupBase>, 'spec'> & { spec: ExamSpec };
