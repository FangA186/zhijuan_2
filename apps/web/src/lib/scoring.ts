import { ExamSection } from '../types/spec';

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
  return sections.reduce((acc, s) => acc + (s.count * s.score_each_x100), 0);
}

/**
 * 校验分值配平
 */
export function validateScoreBalance(sections: ExamSection[], targetTotalX100: number): {
  isBalanced: boolean;
  actualTotalX100: number;
  diffX100: number;
} {
  const actual = calculateSectionsTotalX100(sections);
  const diff = actual - targetTotalX100;
  return {
    isBalanced: diff === 0,
    actualTotalX100: actual,
    diffX100: diff,
  };
}
