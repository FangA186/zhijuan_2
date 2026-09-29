import { ScopeSource, SCOPE_SOURCE_LABELS } from '../../lib/sectionScope';

interface Props {
  topics: string[];
  excludedTopics: string[];
  scopeConfirmed: boolean;
  scopeSources: Record<string, ScopeSource>;
  topicInput: string;
  excludedInput: string;
  onScopeConfirmedChange: (confirmed: boolean) => void;
  onTopicInputChange: (value: string) => void;
  onExcludedInputChange: (value: string) => void;
  onAddTopic: () => void;
  onRemoveTopic: (topic: string) => void;
  onAddExcluded: () => void;
  onRemoveExcluded: (topic: string) => void;
  onClearTopics: () => void;
  onClearExcludedTopics: () => void;
}

export function ExamSetupScopeTopics({
  topics, excludedTopics, scopeConfirmed, scopeSources, topicInput, excludedInput,
  onScopeConfirmedChange, onTopicInputChange, onExcludedInputChange, onAddTopic, onRemoveTopic,
  onAddExcluded, onRemoveExcluded, onClearTopics, onClearExcludedTopics,
}: Props) {
  return (
    <>
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="block text-xs font-semibold text-slate-600">
            本次考查知识点（命题目标，共 <strong className="text-emerald-700">{topics.length}</strong> 项）:
          </label>
          {topics.length > 0 && <button type="button" onClick={onClearTopics}
            className="text-[11px] text-slate-400 hover:text-rose-600 transition">清空考查点</button>}
        </div>
        <div className="flex flex-wrap gap-2 mb-2">
          {topics.length === 0 ? (
            <span className="text-xs text-slate-400 italic py-1">暂无知识点，请从上方章节树勾选导入或在下方手动输入添加</span>
          ) : topics.map((topic) => {
            const source = scopeSources[topic] || 'manual';
            return (
              <span key={topic} className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-2xs">
                <span>{topic}</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${source === 'manual' ? 'bg-slate-100 text-slate-500' : 'bg-emerald-100 text-emerald-700'}`}>
                  {SCOPE_SOURCE_LABELS[source]}
                </span>
                <button onClick={() => onRemoveTopic(topic)}
                  className="text-emerald-500 hover:text-emerald-800 text-sm font-bold">&times;</button>
              </span>
            );
          })}
        </div>
        <div className="flex gap-2">
          <input type="text" value={topicInput} onChange={(event) => onTopicInputChange(event.target.value)}
            onKeyDown={(event) => event.key === 'Enter' && (event.preventDefault(), onAddTopic())}
            placeholder="手动输入知识点后按回车或点击添加..."
            className="flex-1 border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden" />
          <button type="button" onClick={onAddTopic}
            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold">添加知识点</button>
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input type="checkbox" checked={scopeConfirmed} onChange={(event) => onScopeConfirmedChange(event.target.checked)} />
        我已确认本次考查范围
      </label>

      <div className="pt-3 border-t border-slate-100">
        <div className="flex items-center justify-between mb-1.5">
          <label className="block text-xs font-semibold text-slate-600">
            严禁超纲排除内容（违禁拦截，共 <strong className="text-rose-700">{excludedTopics.length}</strong> 项）:
          </label>
          {excludedTopics.length > 0 && <button type="button" onClick={onClearExcludedTopics}
            className="text-[11px] text-slate-400 hover:text-rose-600 transition">清空排除项</button>}
        </div>
        <div className="flex flex-wrap gap-2 mb-2">
          {excludedTopics.length === 0 ? (
            <span className="text-xs text-slate-400 italic py-1">未设排除项（命题模型将默认在考查知识点范围内生成）</span>
          ) : excludedTopics.map((topic) => (
            <span key={topic} className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-rose-50 text-rose-800 border border-rose-200 shadow-2xs">
              <span>{topic}</span>
              <button onClick={() => onRemoveExcluded(topic)}
                className="text-rose-500 hover:text-rose-800 text-sm font-bold">&times;</button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input type="text" value={excludedInput} onChange={(event) => onExcludedInputChange(event.target.value)}
            onKeyDown={(event) => event.key === 'Enter' && (event.preventDefault(), onAddExcluded())}
            placeholder="输入禁止出现的概念/公式..."
            className="flex-1 border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-800 focus:ring-2 focus:ring-rose-500 focus:outline-hidden" />
          <button type="button" onClick={onAddExcluded}
            className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold">添加排除项</button>
        </div>
      </div>
    </>
  );
}

