import React from 'react';
import { Sparkles } from 'lucide-react';
import { ExamSpec } from '../types/spec';
import { FoolproofSetupForm } from './foolproof-setup/FoolproofSetupForm';
import { useFoolproofSetupBase } from './foolproof-setup/useFoolproofSetupBase';

interface FoolproofSetupProps {
  onStartGeneration: (spec: ExamSpec) => void;
  generationConfigured: boolean;
}

export const FoolproofSetup: React.FC<FoolproofSetupProps> = props => {
  const state = useFoolproofSetupBase();
  if (!state.spec) return (
    <div className="flex items-center justify-center p-12 text-slate-500 text-sm">
      <Sparkles className="w-5 h-5 animate-spin mr-2 text-brand-500" />正在准备备课出卷工作台...
    </div>
  );
  return <FoolproofSetupForm state={{ ...state, spec: state.spec }} {...props} />;
};
