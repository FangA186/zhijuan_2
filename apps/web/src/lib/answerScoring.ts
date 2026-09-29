export function selectionLabels(question: any, answer: any): string[] {
  const selected = answer?.correct_option_ids || answer?.selected_option_ids || [];
  if (!Array.isArray(selected)) return [];
  return selected.map((id: string) => {
    const index = (question?.options || []).findIndex((option: any) => option.id === id);
    return question ? (index < 0 ? '?' : String.fromCharCode(65 + index)) : id.replace(/^opt_/i, '').toUpperCase();
  });
}

export function answerScoring(question: any, answer: any) {
  if (answer?.scoring_mode === 'exclusive') {
    const partial = answer.partial_score_x100;
    if (!Number.isSafeInteger(partial) || partial < 0 || partial >= question.score_x100)
      return { exclusive: true, rows: [], warning: '评分档位不完整或越界，需核对' };
    const selected: string[] = answer.correct_option_ids || [];
    const labels = selectionLabels(question, answer);
    const invalid = Boolean(answer.rubric?.length) || new Set(selected).size !== selected.length || labels.includes('?') || (question.kind === 'multiple_choice' && labels.length < 2);
    return { exclusive: true, warning: invalid ? '正确选项记录不完整，需核对' : '', rows: [
      { description: `全部选对${labels.length ? `（${labels.join('、')}）` : ''}`, score_x100: question.score_x100 },
      ...(question.kind === 'multiple_choice' ? [{ description: '少选且无错选', score_x100: partial }] : []),
      { description: '有错选或未作答', score_x100: 0 },
    ] };
  }
  const rubric = answer?.rubric || answer?.scoring_rubric || [];
  return { exclusive: false, warning: '', rows: rubric.map((r: any) => ({
    description: r.description || r.criterion || '', score_x100: r.score_x100,
  })) };
}
