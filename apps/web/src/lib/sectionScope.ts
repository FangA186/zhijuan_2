import { concreteTopics } from './topicPlanning.ts';
import type { TaughtScope, ExamSection } from '../types/spec';
// 显式 .ts 扩展名：node --test 直跑 .ts 文件时需要可解析的运行时导入
import { sectionItemScores } from './scoring.ts';

/** Keep section-specific choices where valid; reassign stale sections inside the selected scope. */
export function alignSectionTopics<T extends { topics: string[] }>(sections: T[], topics: string[]): T[] {
  return sections.map(section => {
    const selected = concreteTopics(section.topics).filter(topic => concreteTopics(topics).includes(topic));
    return { ...section, topics: selected.length ? selected : concreteTopics(topics) };
  });
}

/**
 * 已选范围项的最小来源标记：教材章节 / 手动补充 / 模板建议。
 * 标记只存在浏览器 localStorage（按教材上下文分键），不写入 spec——
 * contracts/exam-spec.schema.json 对 taught_scope 是 additionalProperties:false，
 * 写进 taught_scope 会被后端校验拒绝；后端契约不归本任务改。
 * 未标记项一律视为「手动补充」，保证永不因来源未知而静默删除。
 */
export type ScopeSource = 'textbook' | 'manual' | 'template';

export const SCOPE_SOURCE_LABELS: Record<ScopeSource, string> = {
  textbook: '教材章节',
  manual: '手动补充',
  template: '模板建议',
};

const SOURCES_STORAGE_KEY = 'zhijuan_scope_topic_sources';
type SourcesStore = Record<string, Record<string, ScopeSource>>;

/** 教材上下文标识：同一学段+同一教材+同一学科内共享一套来源标记。 */
export function topicSourceContext(stage: string, materialId: string | undefined, subjectCode: string): string {
  return `${stage}|${materialId || 'none'}|${subjectCode}`;
}

function readStore(): SourcesStore {
  try {
    const raw = localStorage.getItem(SOURCES_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as SourcesStore) : {};
  } catch {
    return {};
  }
}

function writeStore(store: SourcesStore): void {
  try {
    localStorage.setItem(SOURCES_STORAGE_KEY, JSON.stringify(store));
  } catch {
    // localStorage 不可用（隐私模式等）时标记短暂失效，降级为全部 manual，不抛错
  }
}

/** 为某教材上下文下的一组范围项登记来源标记。 */
export function markTopicSources(contextId: string, topics: string[], source: ScopeSource): void {
  const store = readStore();
  const current: Record<string, ScopeSource> = { ...(store[contextId] || {}) };
  for (const topic of topics) current[topic] = source;
  store[contextId] = current;
  writeStore(store);
}

/** 读取已选范围的来源标记（按上下文查询）；未标记项视为 manual。 */
export function scopeSourcesOf(scope: TaughtScope, contextId?: string): Record<string, ScopeSource> {
  const marked: Record<string, ScopeSource> = contextId ? (readStore()[contextId] || {}) : {};
  const result: Record<string, ScopeSource> = {};
  for (const topic of scope.topics) {
    result[topic] = marked[topic] ?? 'manual';
  }
  return result;
}

/** 切换学段/教材时的范围划分：失效项 = 旧上下文中的教材章节来源 + 模板建议来源；手动补充始终保留。 */
export interface ScopeSwitchPartition {
  staleTextbook: string[];
  staleTemplate: string[];
  manual: string[];
}

export function scopeSwitchPartition(scope: TaughtScope, fromContextId?: string): ScopeSwitchPartition {
  const sources = scopeSourcesOf(scope, fromContextId);
  const staleTextbook: string[] = [];
  const staleTemplate: string[] = [];
  const manual: string[] = [];
  for (const topic of scope.topics) {
    if (sources[topic] === 'textbook') staleTextbook.push(topic);
    else if (sources[topic] === 'template') staleTemplate.push(topic);
    else manual.push(topic);
  }
  return { staleTextbook, staleTemplate, manual };
}

export type ScopeSwitchMode = 'clear' | 'keep';

/**
 * 切换后的范围处理（fromContextId=旧教材上下文，toContextId=新上下文）：
 * - clear：清除失效项（旧教材章节 + 模板建议来源），保留手动补充项；
 * - keep：保留全部旧范围项，由教师再次人工确认；
 * 保留项会原样迁移到新上下文，保证后续切回时仍能区分来源。
 * 两种方式都强制 scope_confirmed=false；手动项永远不会被本函数静默删除。
 */
export function applyScopeSwitch(
  scope: TaughtScope,
  mode: ScopeSwitchMode,
  fromContextId?: string,
  toContextId?: string,
): TaughtScope {
  const partition = scopeSwitchPartition(scope, fromContextId);
  const topics = mode === 'clear' ? partition.manual : scope.topics;
  if (toContextId) {
    const sources = scopeSourcesOf(scope, fromContextId);
    const bySource: Record<ScopeSource, string[]> = { textbook: [], manual: [], template: [] };
    for (const topic of topics) bySource[sources[topic] ?? 'manual'].push(topic);
    (Object.keys(bySource) as ScopeSource[]).forEach((source) => {
      if (bySource[source].length > 0) markTopicSources(toContextId, bySource[source], source);
    });
  }
  return { ...scope, topics, scope_confirmed: false };
}

/**
 * 逐题核对：把分值与题数的具体矛盾翻译成可读的中文问题列表。
 * 覆盖：题数与逐题分值条数不符（如 24 题配 23 条 scores）、负数/小数/非整数 score_x100、
 * 题型总分为 0、逐题分值之和与题型总分不一致、题型合计与试卷设定总分不一致。
 */
export function sectionIssues(sections: ExamSection[], targetTotalX100: number, partialScoreX100 = 0): string[] {
  const issues: string[] = [];
  if (!Number.isSafeInteger(partialScoreX100) || partialScoreX100 < 0) issues.push('多选题少选得分必须是非负分值');

  sections.forEach((sec, idx) => {
    const label = `第 ${idx + 1} 题组「${sec.title || sec.id}」`;
    if (!Number.isSafeInteger(sec.count) || sec.count <= 0 || sec.count > 100) {
      issues.push(`${label}：题数 ${sec.count} 不是 1–100 的有效整数`);
      return;
    }
    if (sec.item_scores_x100 !== undefined) {
      if (sec.item_scores_x100.length !== sec.count) {
        issues.push(`${label}：题数 ${sec.count} 题却配了 ${sec.item_scores_x100.length} 条逐题分值，数量不一致`);
      }
      const bad = sec.item_scores_x100.filter(n => !Number.isSafeInteger(n) || n <= 0);
      if (bad.length > 0) {
        issues.push(`${label}：逐题分值中含有负数或小数分值 ${bad.join('、')}（score_x100 必须为正整数）`);
      }
    } else if (!Number.isSafeInteger(sec.score_each_x100) || sec.score_each_x100 <= 0 || sec.score_each_x100 > 100000) {
      issues.push(`${label}：每题分值 ${sec.score_each_x100} 不是有效的正整数分值单位（score_x100）`);
    }
    if (sec.total_score_x100 !== undefined && (!Number.isSafeInteger(sec.total_score_x100) || sec.total_score_x100 <= 0)) {
      issues.push(`${label}：题型总分 ${sec.total_score_x100} 不是有效的正整数分值单位（score_x100）`);
    }
  });
  try {
    for (const section of sections.filter(s => s.question_type === 'multiple_choice')) {
      if (sectionItemScores(section).some(score => partialScoreX100 >= score)) issues.push('多选题少选得分必须小于每题满分');
    }
    const actual = sections.reduce((acc, sec) => acc + sectionItemScores(sec).reduce((a, b) => a + b, 0), 0);
    if (actual !== targetTotalX100) {
      const diff = Math.abs(targetTotalX100 - actual);
      issues.push(`题型合计 ${actual / 100} 分，试卷设定 ${targetTotalX100 / 100} 分，相差 ${diff / 100} 分`);
    }
  } catch {
    // 逐题分值问题已在上方逐条说明，合计无法计算时不再重复
  }
  return issues;
}
