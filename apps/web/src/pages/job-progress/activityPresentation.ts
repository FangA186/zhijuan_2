import type { JobEventLog } from '../../types/job';

const roleNames: Record<string, string> = { planner: '规划', author: '命题', solver: '盲解', reviewer: '审核', system: '系统' };
const phaseText: Record<string, string> = { author: '正在编写题目', solver: '正在独立解题', reviewer: '正在审核题目与检查结果' };

function blocks(items: any[] = []): string {
  return items.map(item => item.text ?? item.latex ?? '').filter(Boolean).join('\n');
}
function partialText(raw: string): string {
  const parts: string[] = [];
  const pattern = /"(text|latex|description|summary|derived_answer)"\s*:\s*"((?:\\.|[^"\\])*)(?:"|$)/g;
  for (const match of raw.matchAll(pattern)) {
    try { parts.push(JSON.parse(`"${match[2]}"`)); } catch { /* Keep the previous complete text until the escape closes. */ }
  }
  return parts.filter(Boolean).join('\n\n');
}

export function readableOutput(raw: string): string {
  if (!raw.trim().startsWith('{')) return raw;
  try {
    const value = JSON.parse(raw);
    if (value.public) {
      const question = value.public;
      const lines = [blocks(question.prompt)];
      (question.options || []).forEach((option: any, index: number) => lines.push(`${String.fromCharCode(65 + index)}. ${blocks(option.content)}`));
      (value.private?.answers || []).forEach((answer: any) => {
        const options = (answer.correct_option_ids || []).map((id: string) => {
          const index = (question.options || []).findIndex((option: any) => option.id === id);
          return index < 0 ? id : String.fromCharCode(65 + index);
        });
        const accepted = (answer.accepted_answers || []).map((a: any) => a.value);
        if (options.length || accepted.length) lines.push(`参考答案：${[...options, ...accepted].join('、')}`);
        lines.push(blocks(answer.solution));
        (answer.rubric || []).forEach((r: any) => lines.push(r.description));
      });
      return lines.filter(Boolean).join('\n\n');
    }
    if (value.summary) return [value.summary, ...(value.issues || [])].join('\n\n');
    if (typeof value.derived_answer === 'string') return [`解答：${value.derived_answer}`, blocks(value.steps)].filter(Boolean).join('\n\n');
    return partialText(raw) || raw;
  } catch { return partialText(raw); }
}

export function activityTitle(log: JobEventLog): string {
  const role = roleNames[log.role] || log.role;
  const number = log.slot_id?.match(/(\d+)$/)?.[1];
  return `${role}${number ? ` · 第${Number(number)}题` : ''}${log.attempt ? ` · 第${log.attempt}轮修订` : ''}`;
}

export function activityText(log: JobEventLog): string {
  if (log.kind === 'phase_started') return phaseText[log.role] || '开始执行';
  if (log.kind === 'hermes_run_admitted') return '调用已受理';
  if (log.kind === 'repair_reserved') return '开始按审核意见修订，完成后重新检查。';
  if (log.kind === 'completed') return '执行结束';
  if (log.kind === 'tool.started') return `执行工具：${log.data?.tool || ''}`;
  if (log.kind === 'tool.completed') return `工具执行结束：${log.data?.tool || ''}`;
  if (log.kind === 'run.result' && !log.data?.output) return String(log.data?.error || `执行状态：${log.data?.status || '未知'}`);
  return readableOutput(log.message);
}

export function timelineLogs(logs: JobEventLog[]): JobEventLog[] {
  const key = (log: JobEventLog) => `${log.slot_id}:${log.role}:${log.attempt || 0}`;
  const finals = new Map(logs.filter(log => log.kind === 'run.result' && log.data?.output).map(log => [key(log), log]));
  const emitted = new Set<string>();
  return logs.flatMap(log => {
    if (['hermes_run_admitted', 'run.started', 'run.completed', 'completed'].includes(log.kind || '')) return [];
    if (log.kind === 'message.delta' || log.kind === 'run.result' && log.data?.output) {
      const id = key(log);
      if (emitted.has(id)) return [];
      emitted.add(id);
      return [finals.get(id) || log];
    }
    return [log];
  });
}
