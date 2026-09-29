import React from 'react';
import { Header } from './components/Header';
import { ErrorBoundary } from './components/ErrorBoundary';
import { FoolproofSetup } from './pages/FoolproofSetup';
import { ExamPaperWorkbench } from './pages/ExamPaperWorkbench';
import { useAppState } from './app/useAppState';

export const App: React.FC = () => {
  const state = useAppState();
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Header
        currentRole={state.currentRole}
        onRoleChange={state.setCurrentRole}
        onResetData={state.handleResetData}
        onNewExam={state.handleNewExam}
        titleInfo={state.titleInfo}
        generationState={state.generationState}
        generationChecking={state.generationChecking}
        onRecheckGeneration={state.handleRecheckGeneration}
        showNewExamButton={state.appView === 'paper'}
      />
      <main className="flex-1">
        {state.draftError && <div role="alert" className="mx-auto max-w-4xl rounded-lg bg-rose-50 p-3 text-rose-800">{state.draftError}</div>}
        <ErrorBoundary>
          {state.appView === 'setup' && (
            <FoolproofSetup
              key={`setup-${state.draftReloadNonce}`}
              onStartGeneration={state.handleStartGeneration}
              generationConfigured={state.generationState?.configured === true}
            />
          )}
          {state.appView === 'paper' && state.draft && (
            <ExamPaperWorkbench
              spec={state.draft}
              candidates={state.candidates}
              isGeneratingInitially={state.isGenerating}
              onCandidatesUpdated={state.handleCandidatesUpdated}
            />
          )}
        </ErrorBoundary>
      </main>
      <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-400 print:hidden">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>知卷 · 智能试卷生成系统 (教师极简版)</span>
          <span>AI 原创候选 · 独立盲解 · 检查结果需教师复核</span>
        </div>
      </footer>
      {state.etagConflict && (
        <div role="alertdialog" aria-modal="true" className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div role="document" className="max-w-md w-full rounded-2xl bg-white p-5 shadow-xl space-y-4">
            <h2 className="text-base font-bold text-slate-900">草稿版本冲突</h2>
            <p className="text-sm text-slate-600">{state.etagConflict}</p>
            <div className="flex gap-2 justify-end">
              <button type="button" onClick={() => state.setEtagConflict(null)} className="px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-sm font-semibold rounded-xl transition cursor-pointer">
                保留本地副本
              </button>
              <button type="button" onClick={state.handleReloadDraft} className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold rounded-xl transition cursor-pointer">
                重载最新草稿
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
