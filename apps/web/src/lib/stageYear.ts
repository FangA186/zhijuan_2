import type { Stage } from '../types/spec';

/** stage_year is counted within the selected school stage. */
export function stageYearFromGrade(stage: Stage, label: string): number | null {
  const digit = (value: string): number => ({ 一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9 }[value] ?? Number(value));
  if (stage === 'primary') {
    const match = label.match(/([一二三四五六1-6])年级/);
    return match ? digit(match[1]) : null;
  }
  if (stage === 'junior') {
    const grade = label.match(/([七八九789])年级/);
    if (grade) return digit(grade[1]) - 6;
    const local = label.match(/(?:初中?)([一二三123])(?:年级)?/);
    return local ? digit(local[1]) : null;
  }
  const local = label.match(/(?:高|高中)([一二三123])(?:年级)?/);
  return local ? digit(local[1]) : null;
}

export function gradeLabelForStage(stage: Stage, year: number): string {
  const names = ['一', '二', '三', '四', '五', '六', '七', '八', '九'];
  return stage === 'senior' ? `高${names[year - 1]}` : `${names[(stage === 'junior' ? year + 6 : year) - 1]}年级`;
}

export function subjectCodeFromLabel(label: string): string | null {
  const subjects: Record<string, string> = {
    数学: 'math', 语文: 'chinese', 英语: 'english', 物理: 'physics',
    化学: 'chemistry', 生物学: 'biology', 生物: 'biology', 历史: 'history',
    地理: 'geography', 道德与法治: 'moral', 思想政治: 'politics', 科学: 'science',
  };
  const name = Object.keys(subjects).find(subject => label.includes(subject));
  return name ? subjects[name] : null;
}
