import { answerScoring } from '../lib/answerScoring';
import { formatScoreX100 } from '../lib/scoring';

export function AnswerScoring({ question, answer }: { question: any; answer: any }) {
  const scoring = answerScoring(question, answer);
  if (!scoring.rows.length && !scoring.warning) return null;
  return <section aria-label="评分规则" className="mt-2 rounded-lg border border-brand-200 bg-brand-50/60 p-3 text-xs space-y-2">
    <h4 className="font-semibold">{scoring.exclusive ? '互斥评分档位（只计一档，不累加）' : '累加采分点'}</h4>
    {scoring.warning && <p role="alert" className="text-rose-700">{scoring.warning}</p>}
    <ul className="space-y-1">
      {scoring.rows.map((row: any, index: number) => <li key={index} className="flex items-start justify-between gap-3">
        <span>{scoring.exclusive ? '' : `第${index + 1}步：`}{row.description}</span>
        <span className="shrink-0 font-semibold">{scoring.exclusive ? '' : '+'}{formatScoreX100(row.score_x100)}分</span>
      </li>)}
    </ul>
  </section>;
}
