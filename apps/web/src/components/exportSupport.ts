import { selectionLabels } from '../lib/answerScoring';
import { GeneratedCandidate } from '../types/candidate';
import { ExamSpec } from '../types/spec';
import { formatScoreX100 } from '../lib/scoring';

export const getSafeAnswerText = (ans: any, cand: any): string => {
  if (!ans && !cand) return '见解析';
  const labels = selectionLabels(cand?.public, ans);
  if (labels.length) return labels.join('、');
  if (typeof ans?.answer_text === 'string' && ans.answer_text.trim()) return ans.answer_text;
  if (Array.isArray(ans?.accepted_answers) && ans.accepted_answers.length > 0) {
    const first = ans.accepted_answers[0];
    if (typeof first === 'string' && first.trim()) return first;
    if (first && typeof first.value === 'string' && first.value.trim()) return first.value;
  }
  if (typeof cand?.answer === 'string' && cand.answer.trim()) return cand.answer;
  if (cand?.answer && typeof cand.answer.value === 'string') return cand.answer.value;
  return '见解析';
};

export const escapeHtml = (value: unknown): string => String(value ?? '').replace(/[&<>"']/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
})[char]!);

const questionHasAssets = (question: GeneratedCandidate['public']): boolean =>
  !!question.prompt?.some((block) => block.type === 'asset')
  || !!question.options?.some((option) => option.content?.some((block) => block.type === 'asset'))
  || !!question.children?.some(questionHasAssets);

export const candidateHasAssets = (candidate: GeneratedCandidate): boolean =>
  questionHasAssets(candidate.public)
  || !!candidate.private?.answers?.some((answer) => answer.explanation?.some((block) => block.type === 'asset'));

export const downloadJson = (data: unknown, title: string, label: string) => {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${title}_${label}.json`;
  a.click();
  URL.revokeObjectURL(url);
};

export const downloadDocx = (spec: ExamSpec, candidates: GeneratedCandidate[], fontSizePt: number) => {
  const questionsHtml = candidates.map((cand, idx) => {
    const promptText = Array.isArray(cand.public.prompt)
      ? cand.public.prompt.map((p: any) => p.text || '').join('')
      : (cand.public.prompt || '');
    const optionsHtml = (cand.public.options || []).map((opt: any) =>
      `<div><b>${escapeHtml(opt.label || String(opt.id || '').replace('opt_', ''))}.</b> ${escapeHtml(Array.isArray(opt.content) ? opt.content.map((x: any) => x.text || '').join('') : (opt.content || opt.text || ''))}</div>`
    ).join('');
    const ans = cand.private?.answers?.[0] || {};
    const ansText = getSafeAnswerText(ans, cand);
    const expText = Array.isArray(ans.explanation) ? ans.explanation.map((x: any) => x.text || '').join('') : (ans.explanation || '');
    return `<div style="margin-bottom: 14pt;"><div><b>${idx + 1}.</b> ${escapeHtml(promptText)} (${formatScoreX100(cand.public.score_x100)}分)</div>${optionsHtml ? `<div style="margin-left: 18pt; margin-top: 4pt;">${optionsHtml}</div>` : ''}<div style="margin-top: 6pt; background: #f8fafc; padding: 6pt; border-left: 3pt solid #0284c7;"><div><b>【参考答案】:</b> ${escapeHtml(ansText)}</div>${expText ? `<div><b>【详细解析】:</b> ${escapeHtml(expText)}</div>` : ''}</div></div>`;
  }).join('');
  const html = `<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'><head><meta charset='utf-8'><title>${escapeHtml(spec.title)}</title><style>body { font-family: 'SimSun', serif; font-size: ${fontSizePt}pt; line-height: 1.6; } h1 { text-align: center; font-size: 16pt; font-weight: bold; margin-bottom: 6pt; } .meta { text-align: center; font-size: 10pt; color: #555; margin-bottom: 20pt; }</style></head><body><h1>${escapeHtml(spec.title)}</h1><div class="meta">考试时长: ${spec.duration_minutes || 90} 分钟 | 满分: ${formatScoreX100(spec.total_score_x100)} 分</div>${questionsHtml}</body></html>`;
  const blob = new Blob(['\ufeff' + html], { type: 'application/msword' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${spec.title}.doc`;
  a.click();
  URL.revokeObjectURL(url);
};
