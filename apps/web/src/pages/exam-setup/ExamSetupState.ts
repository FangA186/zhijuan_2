import { useEffect, useState } from 'react';
import { ExamSpec, ExamBlueprint, BlueprintSlot } from '../../types/spec';
import { api } from '../../lib/api';
import { GenerationRuntimeState } from '../../types/job';
import { PendingScopeSwitch } from './ExamSetupTypes';

export function useExamSetupState() {
  const [spec, setSpec] = useState<ExamSpec | null>(null);
  const [blueprint, setBlueprint] = useState<ExamBlueprint | null>(null);
  const [editingSlot, setEditingSlot] = useState<BlueprintSlot | null>(null);
  const [isGeneratingBlueprint, setIsGeneratingBlueprint] = useState(false);
  const [topicInput, setTopicInput] = useState('');
  const [excludedInput, setExcludedInput] = useState('');
  const [isTextbookModalOpen, setIsTextbookModalOpen] = useState(false);
  const [readiness, setReadiness] = useState<GenerationRuntimeState | null>(null);
  const [readinessChecking, setReadinessChecking] = useState(false);
  const [scopeNotice, setScopeNotice] = useState('');
  const [pendingScopeSwitch, setPendingScopeSwitch] = useState<PendingScopeSwitch | null>(null);

  useEffect(() => {
    const load = async () => {
      const loadedSpec = await api.getExamSpec();
      setSpec(loadedSpec);
      const loadedBlueprint = await api.getBlueprint();
      setBlueprint(loadedBlueprint);
    };
    load();
  }, []);

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
    return () => { cancelled = true; };
  }, []);

  const refreshReadiness = async () => {
    setReadinessChecking(true);
    const state = await api.fetchGenerationReadiness();
    setReadiness(state);
    setReadinessChecking(false);
  };

  return {
    spec, setSpec, blueprint, setBlueprint, editingSlot, setEditingSlot,
    isGeneratingBlueprint, setIsGeneratingBlueprint, topicInput, setTopicInput,
    excludedInput, setExcludedInput, isTextbookModalOpen, setIsTextbookModalOpen,
    readiness, setReadiness, readinessChecking, setReadinessChecking, refreshReadiness,
    scopeNotice, setScopeNotice, pendingScopeSwitch, setPendingScopeSwitch,
  };
}

