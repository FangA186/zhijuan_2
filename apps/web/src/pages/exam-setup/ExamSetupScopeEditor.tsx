import { ExamSpec } from '../../types/spec';
import { ScopeSource } from '../../lib/sectionScope';
import { ChapterTreeScopeSelector } from '../../components/ChapterTreeScopeSelector';
import { ExamSetupScopeTopics } from './ExamSetupScopeTopics';

interface Props {
  spec: ExamSpec;
  scopeSources: Record<string, ScopeSource>;
  topicInput: string;
  excludedInput: string;
  setSpec: (next: ExamSpec) => void;
  onAddTopics: (topics: string[]) => void;
  onAddExcludedTopics: (topics: string[]) => void;
  onAddTopic: () => void;
  onRemoveTopic: (topic: string) => void;
  onAddExcluded: () => void;
  onRemoveExcluded: (topic: string) => void;
  onClearTopics: () => void;
  onClearExcludedTopics: () => void;
  onTopicInputChange: (value: string) => void;
  onExcludedInputChange: (value: string) => void;
}

export function ExamSetupScopeEditor(props: Props) {
  const { spec } = props;
  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-brand-500"></span>
          2. 教学考查知识点与排除约束 (Taught Scope)
        </h2>
        {spec.material_id && <span className="text-xs text-slate-500 hidden sm:inline">
          当前教材: <span className="font-semibold text-brand-700">{spec.textbook}</span>
        </span>}
      </div>
      <ChapterTreeScopeSelector
        materialId={spec.material_id}
        textbookTitle={spec.textbook || spec.title}
        existingTopics={spec.taught_scope.topics}
        existingExcluded={spec.taught_scope.excluded_topics}
        onAddTopics={props.onAddTopics}
        onAddExcludedTopics={props.onAddExcludedTopics}
      />
      <ExamSetupScopeTopics
        topics={spec.taught_scope.topics} excludedTopics={spec.taught_scope.excluded_topics}
        scopeConfirmed={spec.taught_scope.scope_confirmed} scopeSources={props.scopeSources}
        topicInput={props.topicInput} excludedInput={props.excludedInput}
        onScopeConfirmedChange={(confirmed) => props.setSpec({
          ...spec, taught_scope: { ...spec.taught_scope, scope_confirmed: confirmed },
        })}
        onTopicInputChange={props.onTopicInputChange} onExcludedInputChange={props.onExcludedInputChange}
        onAddTopic={props.onAddTopic} onRemoveTopic={props.onRemoveTopic}
        onAddExcluded={props.onAddExcluded} onRemoveExcluded={props.onRemoveExcluded}
        onClearTopics={props.onClearTopics} onClearExcludedTopics={props.onClearExcludedTopics}
      />
    </div>
  );
}
