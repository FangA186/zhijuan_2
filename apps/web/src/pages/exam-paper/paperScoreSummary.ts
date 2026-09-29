export function sumGeneratedSectionScores(sectionTotals: number[]): number {
  return sectionTotals.reduce((sum, score) => sum + score, 0);
}
