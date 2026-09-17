import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { StageNav } from './components/StageNav';
import { ExamSetup } from './pages/ExamSetup';
import { JobProgress } from './pages/JobProgress';
import { ExamEditor } from './pages/ExamEditor';
import { Review } from './pages/Review';
import { History } from './pages/History';
import { api } from './lib/api';
import { ExamSpec } from './types/spec';
import { GeneratedCandidate } from './types/candidate';

export const App: React.FC = () => {
  const [currentStage, setCurrentStage] = useState<number>(1);
  const [currentRole, setCurrentRole] = useState<'teacher' | 'reviewer' | 'admin'>('teacher');
  const [spec, setSpec] = useState<ExamSpec | null>(null);
  const [candidates, setCandidates] = useState<GeneratedCandidate[]>([]);

  useEffect(() => {
    loadAppState();
  }, []);

  const loadAppState = async () => {
    const s = await api.getExamSpec();
    setSpec(s);
    const c = await api.getCandidates();
    setCandidates(c);
  };

  const handleResetData = () => {
    if (window.confirm('确定要重置当前工作台演练数据为初始样例（九年级数学）吗？')) {
      api.resetMockData();
      window.location.reload();
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Global Header */}
      <Header
        currentRole={currentRole}
        onRoleChange={setCurrentRole}
        onResetData={handleResetData}
        currentStage={currentStage}
        onStageSelect={setCurrentStage}
      />

      {/* Stage Progression Bar */}
      <StageNav
        currentStage={currentStage}
        onStageChange={setCurrentStage}
      />

      {/* Stage Content Switcher */}
      <main className="flex-1 pb-16">
        {currentStage === 1 && (
          <ExamSetup
            onBlueprintConfirmed={() => {
              setCurrentStage(2);
            }}
          />
        )}

        {currentStage === 2 && (
          <JobProgress
            onGoToEditor={() => {
              setCurrentStage(3);
            }}
          />
        )}

        {currentStage === 3 && (
          <ExamEditor
            onGoToReview={() => {
              setCurrentStage(4);
            }}
          />
        )}

        {currentStage === 4 && spec && (
          <Review
            spec={spec}
            onPublishSuccess={() => {
              setCurrentStage(5);
            }}
          />
        )}

        {currentStage === 5 && spec && (
          <History
            spec={spec}
            candidates={candidates}
            onNewExam={() => {
              api.resetMockData();
              setCurrentStage(1);
              window.location.reload();
            }}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>知卷 · Hermes AI 原创命题工作台 (v1.4 前端界面)</span>
          <span>严格原创生成 · 独立盲解验证 · 分值按 score_x100 整数计算</span>
        </div>
      </footer>
    </div>
  );
};

export default App;
