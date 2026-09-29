import type { Dispatch, SetStateAction } from 'react';
import type { ExamSpec } from '../types/spec';
import { sectionItemScores, parseScoreToX100, formatScoreX100 } from '../lib/scoring';

export function MultipleChoiceScoringField({ spec, setSpec }: {
  spec: ExamSpec; setSpec: Dispatch<SetStateAction<ExamSpec | null>>;
}) {
  const sections = spec.sections.filter(s => s.question_type === 'multiple_choice');
  if (!sections.length) return null;
  let max = 0;
  try { max = Math.min(...sections.flatMap(sectionItemScores)); } catch { /* Existing score diagnostics cover invalid sections. */ }
  const partial = spec.multiple_choice_partial_score_x100 ?? 0;
  return <div className="rounded-xl border border-slate-200 p-3 text-sm space-y-2">
    <label htmlFor="multiple-choice-partial" className="block font-semibold">多选题少选且无错选得分（分）</label>
    <input id="multiple-choice-partial" name="multiple_choice_partial_score" type="number" min="0" max={Math.max(0,(max-1)/100)} step="0.5"
      value={formatScoreX100(partial)} onChange={event => setSpec({ ...spec,
        multiple_choice_partial_score_x100: parseScoreToX100(event.target.value),
        taught_scope: { ...spec.taught_scope, scope_confirmed: false },
      })} className="w-full rounded-lg border border-slate-300 px-3 py-2" />
    <p className="text-xs text-slate-600">全对按每题满分；错选或未答为0分。各档互斥，不相加。未设置少选分时按0分，请在出题前确认。</p>
    {partial >= max && <p role="alert" className="text-xs text-rose-700">少选得分必须小于每道多选题的满分。</p>}
  </div>;
}
