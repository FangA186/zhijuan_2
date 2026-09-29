import labels from '../../../../configs/template-topic-labels.json' with { type: 'json' };
import { sectionItemScores } from './scoring.ts';
import type { ExamSpec, ExamSection } from '../types/spec';

export const genericTopicLabels = new Set<string>(labels);
export const concreteTopics = (topics: string[]) => topics.filter(topic => !genericTopicLabels.has(topic.trim()));

export function alignConcreteSections(sections: ExamSection[], topics: string[]): ExamSection[] {
  const allowed = concreteTopics(topics);
  return sections.map(section => {
    const selected = concreteTopics(section.topics).filter(topic => allowed.includes(topic));
    return { ...section, topics: selected.length ? selected : [...allowed] };
  });
}

export function repairTemplateTopicScope(spec: ExamSpec): ExamSpec | null {
  const topics = concreteTopics(spec.taught_scope.topics);
  const legacy = spec.sections.some(section => section.topics.some(topic => genericTopicLabels.has(topic)));
  const sections = alignConcreteSections(legacy ? mergeScoreParts(spec.sections) : spec.sections, topics);
  if (JSON.stringify(topics) === JSON.stringify(spec.taught_scope.topics) &&
      JSON.stringify(sections) === JSON.stringify(spec.sections)) return null;
  return { ...spec, sections, taught_scope: { ...spec.taught_scope, topics, scope_confirmed: false } };
}

export function topicLabel(topic?: string): string {
  return !topic || genericTopicLabels.has(topic.trim()) ? '未绑定具体考点（旧计划）' : topic;
}

// Saved unequal-score sections are contiguous parts of the same imported section.
function mergeScoreParts(sections: ExamSection[]): ExamSection[] {
  const result: ExamSection[] = [];
  for (const section of sections) {
    const base = section.id.replace(/_part_\d+$/, '');
    const previous = result.at(-1);
    if (base !== section.id && previous?.id === base && previous.title === section.title && previous.question_type === section.question_type) {
      const scores = [...sectionItemScores(previous), ...sectionItemScores(section)];
      result[result.length - 1] = { ...previous, count: scores.length, item_scores_x100: scores,
        total_score_x100: scores.reduce((sum, score) => sum + score, 0),
        topics: [...new Set([...previous.topics, ...section.topics])] };
    } else result.push({ ...section, id: base });
  }
  return result;
}
