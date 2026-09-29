import React, { useEffect, useState } from 'react';
import { ArrowRight, Eye, Info, ShieldCheck } from 'lucide-react';
import { GeneratedCandidate } from '../types/candidate';
import { ValidationRecord } from '../types/validation';
import { api } from '../lib/api';
import { makePublicProjection } from '../lib/projection';
import { ExamEditorCanvas } from './exam-editor/ExamEditorCanvas';
import { ExamEditorEvidence } from './exam-editor/ExamEditorEvidence';
import { ExamEditorQuestionList } from './exam-editor/ExamEditorQuestionList';

interface ExamEditorProps { onGoToReview: () => void; }
export const ExamEditor: React.FC<ExamEditorProps> = ({ onGoToReview }) => {
  const [candidates, setCandidates] = useState<GeneratedCandidate[]>([]);
  const [validationRecords, setValidationRecords] = useState<Record<string, ValidationRecord>>({});
  const [selectedId, setSelectedId] = useState('slot_01');
  const [isStudentView, setIsStudentView] = useState(false);
  const [activeRightTab, setActiveRightTab] = useState<'answer' | 'blind_solve' | 'evidence'>('answer');
  const [isSaving, setIsSaving] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [saveToast, setSaveToast] = useState<string | null>(null);

  useEffect(() => { void loadData(); }, []);
  const loadData = async () => {
    setCandidates(await api.getCandidates());
    setValidationRecords(await api.getValidationRecords());
  };
  const currentCandidate = candidates.find(candidate => candidate.public.local_id === selectedId) || candidates[0];
  const currentValidation = currentCandidate ? validationRecords[currentCandidate.public.local_id] : null;
  if (!currentCandidate) return <div className="p-8 text-center text-slate-500">正在加载题目编辑工作台...</div>;

  const currentPromptText = currentCandidate.public.prompt.map(block => block.type === 'text' ? block.text : block.type === 'math' ? `$${block.latex}$` : '').join(' ');
  const handlePromptChange = (text: string) => setCandidates(current => current.map(candidate => candidate.public.local_id === currentCandidate.public.local_id
    ? { ...candidate, public: { ...candidate.public, prompt: [{ type: 'text' as const, text }] } }
    : candidate));
  const handleOptionChange = (optionId: string, text: string) => setCandidates(current => current.map(candidate => candidate.public.local_id === currentCandidate.public.local_id
    ? { ...candidate, public: { ...candidate.public, options: candidate.public.options.map(option => option.id === optionId ? { ...option, content: [{ type: 'text' as const, text }] } : option) } }
    : candidate));
  const handleSave = async () => {
    setIsSaving(true);
    await api.updateCandidate(currentCandidate);
    setValidationRecords(await api.getValidationRecords());
    setIsSaving(false);
    setSaveToast('题面已保存！旧自动校验已失效，状态已自动转为 [待复核 REVIEW]。');
    setTimeout(() => setSaveToast(null), 4000);
  };
  const handleRegenerate = async () => {
    setIsRegenerating(true);
    try {
      await api.regenerateQuestion(currentCandidate.public.local_id);
      const [freshCandidates, validations] = await Promise.all([api.getCandidates(), api.getValidationRecords()]);
      setCandidates(freshCandidates);
      setValidationRecords(validations);
      setSaveToast('已完成单题重新构思与独立做题验算！');
    } catch (err) {
      console.error(err);
      setSaveToast('重新生成失败，请检查后端服务与网络连接。');
    } finally {
      setIsRegenerating(false);
      setTimeout(() => setSaveToast(null), 4000);
    }
  };
  const displayedQuestion = isStudentView ? makePublicProjection(currentCandidate) : currentCandidate.public;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-4">
      <header className="bg-white px-6 py-3.5 rounded-2xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-brand-100 text-brand-800">阶段三 · 试卷排版与修改</span>
          <h1 className="text-lg font-bold text-slate-900 flex items-center gap-2">试卷排版与修改 (题目工作台)</h1>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => setIsStudentView(value => !value)} className={`px-3.5 py-1.5 rounded-xl border text-xs font-bold flex items-center gap-1.5 transition ${isStudentView ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs' : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'}`}>
            {isStudentView ? <ShieldCheck className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            <span>{isStudentView ? '学生做卷模式 (答案已隐藏)' : '预览学生作答视角'}</span>
          </button>
          <button onClick={onGoToReview} className="px-4 py-1.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl flex items-center gap-1.5 shadow-sm transition">
            <span>进入智能质检与定稿</span><ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </header>
      {saveToast && <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-center gap-2 animate-fadeIn"><Info className="w-4 h-4 text-amber-600 shrink-0" /><span>{saveToast}</span></div>}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        <ExamEditorQuestionList candidates={candidates} validationRecords={validationRecords} currentId={currentCandidate.public.local_id} onSelect={setSelectedId} />
        <ExamEditorCanvas
          candidate={currentCandidate} promptText={currentPromptText} displayedPrompt={displayedQuestion.prompt}
          isStudentView={isStudentView} isSaving={isSaving} isRegenerating={isRegenerating}
          onPromptChange={handlePromptChange} onOptionChange={handleOptionChange}
          onSave={handleSave} onRegenerate={handleRegenerate}
        />
        <ExamEditorEvidence candidate={currentCandidate} validation={currentValidation} activeTab={activeRightTab} onTabChange={setActiveRightTab} />
      </div>
    </div>
  );
};
