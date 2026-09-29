import type { ExamSection } from '../types/spec';

export function sectionItemScores(section: ExamSection): number[] {
  const valid = (n: number) => Number.isSafeInteger(n) && n > 0;
  if (!valid(section.count) || section.count > 100) throw new Error('题型题数须为 1–100 的整数');
  let scores: number[];
  if (section.item_scores_x100 !== undefined) {
    if (section.item_scores_x100.length !== section.count) throw new Error('逐题分值数量与题数不一致');
    scores = [...section.item_scores_x100];
  } else if (section.total_score_x100 !== undefined) {
    const total = section.total_score_x100;
    if (!valid(total)) throw new Error('题型总分必须是正整数分值单位');
    const base = Math.floor(total / section.count), remainder = total % section.count;
    scores = Array.from({ length: section.count }, (_, i) => base + (i >= section.count - remainder ? 1 : 0));
  } else scores = Array(section.count).fill(section.score_each_x100);
  if (scores.some(score => !valid(score) || score > 100000)) throw new Error('逐题分值必须是有效的正整数分值单位');
  if (section.total_score_x100 !== undefined && scores.reduce((a, b) => a + b, 0) !== section.total_score_x100) {
    throw new Error('逐题分值之和与题型总分不一致，请核对导入模板');
  }
  return scores;
}

/** Encode variable item scores as consecutive uniform sections in the existing API contract. */
export function canonicalSections(sections: ExamSection[]): ExamSection[] {
  const result: ExamSection[] = [];
  for (const section of sections) {
    const scores = sectionItemScores(section);
    const chunks = Array.from({ length: Math.max(1, Math.ceil(section.topics.length / 30)) }, (_, i) => section.topics.slice(i * 30, (i + 1) * 30));
    if (chunks.length > scores.length) throw new Error('当前题数无法覆盖该题型的考点范围，请缩小范围或增加题数');
    const groups: ExamSection[] = [];
    let offset = 0;
    chunks.forEach((topics, chunk) => {
      const count = Math.floor(scores.length / chunks.length) + (chunk < scores.length % chunks.length ? 1 : 0);
      for (let i = 0; i < count; i++) {
        const score = scores[offset++], previous = groups.at(-1);
        if (previous && previous.score_each_x100 === score && previous.topics === topics) previous.count++;
        else groups.push({ id: section.id, title: section.title, question_type: section.question_type, count: 1, score_each_x100: score, topics });
      }
    });
    groups.forEach((group, i) => result.push({ ...group, id: groups.length === 1 ? section.id : `${section.id.slice(0, 50)}_part_${i + 1}` }));
  }
  if (result.length > 30) throw new Error('分值与考点分组超过 30 组，请简化题型配置');
  if (new Set(result.map(s => s.id)).size !== result.length) throw new Error('题型编号重复，请核对模板');
  return result;
}

/**
 * 格式化 score_x100 整数为人类友好的分值字符串。
 * 例: 500 -> "5", 350 -> "3.5", 10000 -> "100", 0 -> "0"
 */
export function formatScoreX100(score_x100: number): string {
  const val = score_x100 / 100;
  // 保持最多两位小数，去掉多余的 0
  return Number(val.toFixed(2)).toString();
}

/**
 * 将人类输入的分值转换为 score_x100 整数。
 * 例: 5 -> 500, 3.5 -> 350, "10" -> 1000
 */
export function parseScoreToX100(score: number | string): number {
  const num = typeof score === 'string' ? parseFloat(score) : score;
  if (isNaN(num) || num < 0) return 0;
  return Math.round(num * 100);
}

/**
 * 计算所有 Section 的总分 (score_x100)
 */
export function calculateSectionsTotalX100(sections: ExamSection[]): number {
  return sections.reduce((acc, s) => acc + sectionItemScores(s).reduce((a, b) => a + b, 0), 0);
}

/**
 * 校验分值配平
 */
export function validateScoreBalance(sections: ExamSection[], targetTotalX100: number): {
  isBalanced: boolean;
  actualTotalX100: number;
  diffX100: number;
  error?: string;
} {
  let actual: number;
  try { actual = calculateSectionsTotalX100(sections); }
  catch (error) { return { isBalanced: false, actualTotalX100: NaN, diffX100: NaN, error: String(error) }; }
  const diff = actual - targetTotalX100;
  return {
    isBalanced: diff === 0,
    actualTotalX100: actual,
    diffX100: diff,
  };
}
