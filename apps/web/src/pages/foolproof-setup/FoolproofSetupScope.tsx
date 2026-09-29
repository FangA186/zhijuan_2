import React from 'react';
import { Plus, X } from 'lucide-react';
import { SCOPE_SOURCE_LABELS, markTopicSources } from '../../lib/sectionScope';
import { ChapterTreeScopeSelector } from '../../components/ChapterTreeScopeSelector';
import { ChineseScopeConfig } from '../../components/ChineseScopeConfig';
import { EnglishScopeConfig } from '../../components/EnglishScopeConfig';
import type { FoolproofSetupModel } from './FoolproofSetupModel';
export const FoolproofSetupScope: React.FC<{ model: FoolproofSetupModel }> = ({ model }) => {
  const { spec, setSpec, setIsTemplateModalOpen, customTopicInput, setCustomTopicInput, handleAddTopic, handleRemoveTopic, totalScore, scopeSources, scopeContext, isChinese, isEnglish } = model;
  return (
    <>
        {isChinese ? (
          /* 语文学科模式：试卷模板 + 指定古诗文篇目 + 选文立意提示词 */
          <div className="space-y-4 pt-4 border-t border-slate-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-brand-600 text-white flex items-center justify-center font-bold text-xs">
                  3
                </span>
                <h2 className="text-base font-bold text-slate-900">
                  语文试卷结构、指定古诗文篇目与命题立意
                </h2>
              </div>
              <span className="text-xs text-slate-500">
                已指定 {spec.chinese_config?.poetry_list?.length || 0} 篇考查篇目
              </span>
            </div>
            <ChineseScopeConfig
              stage={spec.stage}
              config={spec.chinese_config || { poetry_list: [] }}
              onChange={(cfg) => setSpec({ ...spec, chinese_config: cfg })}
              sections={spec.sections}
              totalScore={totalScore}
              durationMinutes={spec.duration_minutes}
              onOpenTemplateModal={() => setIsTemplateModalOpen(true)}
            />
          </div>
        ) : isEnglish ? (
          /* 英语学科模式：试卷模板 + 原版词表维护 + 题材偏好 */
          <div className="space-y-4 pt-4 border-t border-slate-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-brand-600 text-white flex items-center justify-center font-bold text-xs">
                  3
                </span>
                <h2 className="text-base font-bold text-slate-900">
                  英语试卷结构、词表与语篇题材
                </h2>
              </div>
            </div>
            <EnglishScopeConfig
              materialId={spec.material_id}
              config={spec.english_config || {}}
              onChange={(cfg) => setSpec({ ...spec, english_config: cfg })}
              sections={spec.sections}
              totalScore={totalScore}
              durationMinutes={spec.duration_minutes}
              onOpenTemplateModal={() => setIsTemplateModalOpen(true)}
            />
          </div>
        ) : (
          /* 理科与事实学科模式：官方教材目录大纲章节勾选 */
          <div className="space-y-4 pt-4 border-t border-slate-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-brand-600 text-white flex items-center justify-center font-bold text-xs">
                  3
                </span>
                <h2 className="text-base font-bold text-slate-900">选择考查范围与章节</h2>
              </div>
              <span className="text-xs text-slate-500">已选 {(spec.taught_scope?.topics || []).length} 项出卷范围</span>
            </div>
            <ChapterTreeScopeSelector
              materialId={spec.material_id}
              textbookTitle={spec.textbook || spec.title}
              existingTopics={spec.taught_scope?.topics || []}
              existingExcluded={spec.taught_scope?.excluded_topics || []}
              onAddTopics={(newTopics) => {
                setSpec((prev) => {
                  if (!prev) return prev;
                  const merged = Array.from(new Set([...(prev.taught_scope?.topics || []), ...newTopics]));
                  markTopicSources(scopeContext, newTopics, 'textbook');
                  return {
                    ...prev,
                    taught_scope: { ...prev.taught_scope, topics: merged, scope_confirmed: false },
                  };
                });
              }}
              onRemoveTopic={(topicToRemove) => {
                setSpec((prev) => {
                  if (!prev) return prev;
                  return {
                    ...prev,
                    taught_scope: {
                      ...prev.taught_scope,
                      scope_confirmed: false,
                      topics: (prev.taught_scope?.topics || []).filter((t) => t !== topicToRemove),
                    },
                  };
                });
              }}
              onRemoveTopics={(topicsToRemove) => {
                const removeSet = new Set(topicsToRemove);
                setSpec((prev) => {
                  if (!prev) return prev;
                  return {
                    ...prev,
                    taught_scope: {
                      ...prev.taught_scope,
                      scope_confirmed: false,
                      topics: (prev.taught_scope?.topics || []).filter((t) => !removeSet.has(t)),
                    },
                  };
                });
              }}
              onClearAllTopics={() => {
                setSpec((prev) => {
                  if (!prev) return prev;
                  return {
                    ...prev,
                    taught_scope: {
                      ...prev.taught_scope,
                      scope_confirmed: false,
                      topics: [],
                    },
                  };
                });
              }}
            />
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={spec.taught_scope.scope_confirmed}
                onChange={(event) => setSpec({ ...spec, taught_scope: { ...spec.taught_scope, scope_confirmed: event.target.checked } })} />
              我已确认本次考查范围
            </label>
            {(spec.taught_scope?.topics || []).length > 0 && (
              <div className="space-y-1.5 pt-1">
                <div className="text-xs font-semibold text-slate-600">已选入本次试卷的考查范围{scopeSources && Object.values(scopeSources).length > 0 ? '（教材章节 / 手动补充 / 模板建议）' : ''}：</div>
                <div className="flex flex-wrap gap-2">
                  {(spec.taught_scope?.topics || []).map((topic) => {
                    const source = scopeSources[topic] || 'manual';
                    return (
                      <span
                        key={topic}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-50 text-brand-900 text-xs font-medium border border-brand-200 shadow-2xs group"
                      >
                        <span>{topic}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${source === 'textbook' ? 'bg-brand-100 text-brand-700' : source === 'template' ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'}`}>
                          {SCOPE_SOURCE_LABELS[source]}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleRemoveTopic(topic)}
                          className="text-brand-400 hover:text-rose-600 transition cursor-pointer"
                          title="移除此范围"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </span>
                    );
                  })}
                </div>
              </div>
            )}
            <div className="pt-2">
              <div className="text-xs text-slate-500 mb-1.5">或手动补充具体考点：</div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={customTopicInput}
                  onChange={(e) => setCustomTopicInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddTopic();
                    }
                  }}
                  placeholder="输入考点（如：勾股定理逆定理、一元二次方程配方法），按回车添加..."
                  className="flex-1 border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
                />
                <button
                  type="button"
                  onClick={handleAddTopic}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl transition flex items-center gap-1 shrink-0 cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>添加</span>
                </button>
              </div>
            </div>
          </div>
        )}

    </>
  );
};
