import { useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';
import { GeneratedCandidate } from '../types/candidate';
import { ExamSpec } from '../types/spec';
import { GenerationRuntimeState } from '../types/job';

export function useAppState() {
  const [appView, setAppView] = useState<'setup' | 'paper'>('setup');
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentRole, setCurrentRole] = useState<'teacher' | 'reviewer' | 'admin'>('teacher');
  const [draft, setDraft] = useState<ExamSpec | null>(null);
  const [candidates, setCandidates] = useState<GeneratedCandidate[]>([]);
  const [draftError, setDraftError] = useState('');
  const [generationState, setGenerationState] = useState<GenerationRuntimeState | null>(null);
  const [generationChecking, setGenerationChecking] = useState(true);
  const [etagConflict, setEtagConflict] = useState<string | null>(null);
  const [draftReloadNonce, setDraftReloadNonce] = useState(0);
  const disposedRef = useRef(false);

  const reportDraftFailure = (err: unknown) => {
    const e = err as { status?: number; errorType?: string; message?: string };
    if (e?.errorType === 'ETAG_CONFLICT' || e?.status === 412) {
      setEtagConflict('当前草稿版本已在别处更新（版本号冲突）。为避免静默丢弃你的编辑，请选择：');
      return;
    }
    setDraftError(`读取草稿失败：${e?.message || String(err)}`);
  };

  const loadDraftSpec = async (force = false) => {
    try {
      const spec = await api.getExamSpec();
      if (!disposedRef.current) setDraft(current => (force || !current) ? spec : current);
    } catch (err: unknown) {
      console.error(err);
      if (!disposedRef.current) reportDraftFailure(err);
    }
  };

  const syncDraft = async () => {
    try {
      const spec = await api.getExamSpec();
      if (disposedRef.current) return;
      setDraft(current => current ?? spec);
    } catch (err: unknown) {
      console.error(err);
      if (!disposedRef.current) reportDraftFailure(err);
      return;
    }
    try {
      const fresh = await api.getCandidates();
      if (!disposedRef.current) setCandidates(fresh);
    } catch (err) {
      console.error('读取候选失败（不影响草稿编辑）', err);
    }
  };

  const checkResumeJob = async () => {
    try {
      const job = await api.getCurrentJob('current');
      if (disposedRef.current || !job) return;
      setIsGenerating(true);
      setAppView('paper');
    } catch {
      // 读取失败按无任务处理，避免阻塞草稿编辑。
    }
  };

  const refreshGeneration = async () => {
    setGenerationChecking(true);
    const state = await api.fetchGenerationReadiness();
    if (disposedRef.current) return;
    setGenerationState(state);
    setGenerationChecking(false);
  };
  const handleRecheckGeneration = () => { void refreshGeneration(); };

  useEffect(() => {
    disposedRef.current = false;
    void syncDraft();
    void checkResumeJob();
    void refreshGeneration();
    const timer = window.setInterval(() => { void refreshGeneration(); }, 15000);
    return () => {
      disposedRef.current = true;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (appView !== 'setup') return;
    const timer = window.setInterval(() => { void loadDraftSpec(true); }, 10000);
    return () => window.clearInterval(timer);
  }, [appView]);

  const handleReloadDraft = () => {
    setEtagConflict(null);
    setDraftReloadNonce(nonce => nonce + 1);
    void loadDraftSpec(true);
  };
  const handleStartGeneration = (spec: ExamSpec) => {
    setDraft(spec);
    setIsGenerating(true);
    setAppView('paper');
  };
  const handleNewExam = () => {
    setAppView('setup');
    void loadDraftSpec(true);
  };
  const handleResetData = () => {
    if (!window.confirm('确定要重置当前工作台数据为初始样例（九年级数学）吗？')) return;
    api.resetMockData();
    window.location.reload();
  };
  const handleCandidatesUpdated = (fresh: GeneratedCandidate[]) => {
    setCandidates(fresh);
    setIsGenerating(false);
  };

  const gradeSubject = [draft?.grade_label, draft?.subject_label].filter(Boolean).join('');
  const titleInfo = draft
    ? `${gradeSubject ? gradeSubject + ' · ' : ''}满分${((draft.total_score_x100 || 10000) / 100).toFixed(0)}分 (${draft.duration_minutes || 90}分钟)`
    : undefined;

  return {
    appView, isGenerating, currentRole, setCurrentRole, draft, candidates,
    setCandidates, draftError, generationState, generationChecking,
    draftReloadNonce, etagConflict, setEtagConflict, handleReloadDraft,
    handleStartGeneration, handleNewExam, handleResetData,
    handleCandidatesUpdated, handleRecheckGeneration, titleInfo,
  };
}
