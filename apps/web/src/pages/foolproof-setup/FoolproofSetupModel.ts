import type { PlanningJob } from '../../types/planning';
import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import type { ExamBlueprint, ExamSection, ExamSpec, Stage, TextbookSummary } from '../../types/spec';
import type { GenerationRuntimeState } from '../../types/job';
import type { PresetDefinition } from './foolproofSetupPresets';
import type { ScopeSource } from '../../lib/sectionScope';

export type FoolproofTemplate = {
  source: 'uploaded' | 'preset'; name: string; title?: string;
  total_score_x100: number; duration_minutes: number; sections: ExamSection[];
};
export interface FoolproofSetupModel {
  planning: PlanningJob | null; planningError: string; planningBusy: boolean;
  cancelPlanning: () => Promise<void>;
  spec: ExamSpec; setSpec: Dispatch<SetStateAction<ExamSpec | null>>;
  isTextbookModalOpen: boolean; setIsTextbookModalOpen: Dispatch<SetStateAction<boolean>>;
  isTemplateModalOpen: boolean; setIsTemplateModalOpen: Dispatch<SetStateAction<boolean>>;
  presetType: 'quiz' | 'monthly' | 'final';
  templateApplied: { source: 'uploaded' | 'preset'; name: string } | null;
  customTopicInput: string; setCustomTopicInput: Dispatch<SetStateAction<string>>;
  isSubmitting: boolean; preview: ExamBlueprint | null; previewSpec: string;
  setReadiness: Dispatch<SetStateAction<GenerationRuntimeState | null>>;
  setReadinessChecking: Dispatch<SetStateAction<boolean>>;
  pendingScopeSwitch: { nextSpec: ExamSpec; staleTextbook: string[]; staleTemplate: string[]; manual: string[] } | null;
  setPendingScopeSwitch: Dispatch<SetStateAction<FoolproofSetupModel['pendingScopeSwitch']>>;
  startInFlight: MutableRefObject<boolean>;
  handleSelectPreset: (type: 'quiz' | 'monthly' | 'final') => void;
  handleStageSelect: (stage: Stage) => void;
  confirmScopeSwitch: (mode: 'clear' | 'keep') => void;
  handleAddTopic: () => void; handleRemoveTopic: (topic: string) => void;
  handleSelectTextbook: (book: TextbookSummary) => void;
  handleApplyTemplate: (template: FoolproofTemplate) => void;
  handleOneClickGenerate: () => void; handleConfirmAndStart: () => void;
  confirmBlockers: { label: string; hint: string }[]; canStart: boolean;
  totalQuestions: number; totalScore: string;
  scopeSources: Record<string, ScopeSource>; scopeContext: string;
  markTopicSources: (context: string, topics: string[], source: ScopeSource) => void;
  computePresetSummary: (preset: PresetDefinition, topicCount: number) => string;
  isChinese: boolean; isEnglish: boolean;
}
