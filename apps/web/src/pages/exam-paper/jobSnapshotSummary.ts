import type { GenerationJob } from '../../types/job';

export function snapshotSummary(data: GenerationJob) {
  const active = data.slots.find(slot => ['AUTHORING', 'SOLVING'].includes(slot.status));
  const failed = data.slots.filter(slot => slot.status === 'FAIL').length;
  const review = data.slots.filter(slot => slot.status === 'REVIEW_REQUIRED').length;
  const note = `已处理 ${data.completed_slots}/${data.total_slots} 题；${failed} 题失败，${review} 题待教师复核。逐题原因见题槽列表。`;
  return { activeSlotId: active?.slot_id ?? null, note,
    progress: { total: data.total_slots, completed: data.completed_slots, latestNote: note } };
}

export function applySnapshotSummary(data: GenerationJob, setters: {
  setJobId: (id: string) => void;
  setActiveSlotId: (id: string | null) => void;
  setCurrentThinking: (note: string) => void;
  setGenerationProgress: (progress: ReturnType<typeof snapshotSummary>['progress']) => void;
}) {
  const summary = snapshotSummary(data);
  setters.setJobId(data.job_id);
  setters.setActiveSlotId(summary.activeSlotId);
  setters.setCurrentThinking(summary.note);
  setters.setGenerationProgress(summary.progress);
}
