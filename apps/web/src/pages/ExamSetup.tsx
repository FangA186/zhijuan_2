import React from 'react';
import { ExamBlueprint } from '../types/spec';
import { useExamSetupState } from './exam-setup/ExamSetupState';
import { useExamSetupFlowActions } from './exam-setup/ExamSetupFlowActions';
import { useExamSetupScopeActions } from './exam-setup/ExamSetupScopeActions';
import { ExamSetupHeader } from './exam-setup/ExamSetupHeader';
import { ExamSetupAlerts } from './exam-setup/ExamSetupAlerts';
import { ExamSetupBasicInfo } from './exam-setup/ExamSetupBasicInfo';
import { ExamSetupScopeEditor } from './exam-setup/ExamSetupScopeEditor';
import { ExamSetupSectionsEditor } from './exam-setup/ExamSetupSectionsEditor';
import { ExamSetupSummary } from './exam-setup/ExamSetupSummary';
import { TextbookSelectModal } from '../components/TextbookSelectModal';

interface ExamSetupProps {
  onBlueprintConfirmed: (blueprint: ExamBlueprint) => void;
}

export const ExamSetup: React.FC<ExamSetupProps> = ({ onBlueprintConfirmed }) => {
  const state = useExamSetupState();
  const flow = useExamSetupFlowActions({
    spec: state.spec,
    setBlueprint: state.setBlueprint,
    setIsGeneratingBlueprint: state.setIsGeneratingBlueprint,
    setScopeNotice: state.setScopeNotice,
    onBlueprintConfirmed,
    readiness: state.readiness,
    readinessChecking: state.readinessChecking,
    isGeneratingBlueprint: state.isGeneratingBlueprint,
    pendingScopeSwitch: state.pendingScopeSwitch,
  });
  const scope = useExamSetupScopeActions({
    spec: state.spec,
    setSpec: state.setSpec,
    setPendingScopeSwitch: state.setPendingScopeSwitch,
    pendingScopeSwitch: state.pendingScopeSwitch,
    setScopeNotice: state.setScopeNotice,
    topicInput: state.topicInput,
    setTopicInput: state.setTopicInput,
    excludedInput: state.excludedInput,
    setExcludedInput: state.setExcludedInput,
    generateBlueprintForSpec: flow.generateBlueprintForSpec,
  });
  const spec = state.spec;
  const scoreBalance = flow.scoreBalance;
  if (!spec || !scoreBalance) return <div className="p-8 text-center text-slate-500">正在读取规格配置...</div>;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <ExamSetupHeader
        blueprint={state.blueprint}
        isGeneratingBlueprint={state.isGeneratingBlueprint}
        scoreBalanced={scoreBalance.isBalanced}
        hasSectionIssues={flow.issues.length > 0}
        canConfirm={flow.canConfirm}
        onRefreshReadiness={state.refreshReadiness}
        onGenerateBlueprint={flow.handleGenerateBlueprint}
        onConfirm={flow.handleConfirm}
      />
      <ExamSetupAlerts
        readiness={state.readiness}
        readinessChecking={state.readinessChecking}
        confirmBlockers={flow.confirmBlockers}
        scopeNotice={state.scopeNotice}
        pendingScopeSwitch={state.pendingScopeSwitch}
        onConfirmScopeSwitch={scope.confirmScopeSwitch}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <ExamSetupBasicInfo
            spec={spec}
            setSpec={state.setSpec}
            onOpenTextbooks={() => state.setIsTextbookModalOpen(true)}
            onStageChange={scope.handleStageChange}
          />
          <ExamSetupScopeEditor
            spec={spec}
            scopeSources={scope.scopeSources}
            topicInput={state.topicInput}
            excludedInput={state.excludedInput}
            setSpec={(next) => state.setSpec(next)}
            onAddTopics={scope.handleAddTopics}
            onAddExcludedTopics={scope.handleAddExcludedTopics}
            onAddTopic={scope.handleAddTopic}
            onRemoveTopic={scope.handleRemoveTopic}
            onAddExcluded={scope.handleAddExcluded}
            onRemoveExcluded={scope.handleRemoveExcluded}
            onClearTopics={scope.clearTopics}
            onClearExcludedTopics={scope.clearExcludedTopics}
            onTopicInputChange={state.setTopicInput}
            onExcludedInputChange={state.setExcludedInput}
          />
          <ExamSetupSectionsEditor spec={spec} setSpec={state.setSpec} />
        </div>
        <ExamSetupSummary
          spec={spec}
          blueprint={state.blueprint}
          editingSlot={state.editingSlot}
          setEditingSlot={state.setEditingSlot}
          setBlueprint={state.setBlueprint}
          scoreBalance={scoreBalance}
        />
      </div>

      <TextbookSelectModal
        isOpen={state.isTextbookModalOpen}
        onClose={() => state.setIsTextbookModalOpen(false)}
        onSelect={scope.handleSelectTextbook}
        currentMaterialId={spec.material_id}
        initialStage={spec.stage}
      />
    </div>
  );
};
