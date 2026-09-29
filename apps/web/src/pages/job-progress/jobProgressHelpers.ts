import { GenerationJob } from '../../types/job';
import { QuestionKind } from '../../types/spec';

export const QUESTION_KIND_LABELS: Record<QuestionKind, string> = {
  single_choice: '单选题', multiple_choice: '多选题', true_false: '判断题', fill_blank: '填空题',
  solution: '解答题', short_answer: '简答题', essay: '论述题', material_group: '材料综合题组',
};

export function questionKindLabel(kind: QuestionKind | string): string {
  return QUESTION_KIND_LABELS[kind as QuestionKind] ?? String(kind);
}

export function tokensLabelForJob(job: Pick<GenerationJob, 'tokens_used' | 'estimated_cost_cny'> & { usage_status?: string }): { tokens: string; cost: string } {
  const tokens = job.usage_status === 'PARTIAL_UNKNOWN' ? '部分已知（总量未知）'
    : job.tokens_used == null ? '未知' : job.tokens_used.toLocaleString();
  const cost = job.estimated_cost_cny == null ? '未知' : `¥${job.estimated_cost_cny.toFixed(3)}`;
  return { tokens, cost };
}

export const JOB_STATUS_LABELS: Record<GenerationJob['status'], string> = {
  QUEUED: '排队中', RUNNING: '生成中', PAUSED: '已暂停', RECONCILING: '调用结果对账中',
  COMPLETED: '任务完成，题目仍需复核', PARTIAL_FAILED: '部分题目检查失败', CANCELLED: '已取消', FAILED: '任务失败',
};

export const TERMINAL_STATUSES: GenerationJob['status'][] = ['FAILED', 'PARTIAL_FAILED', 'CANCELLED', 'RECONCILING', 'COMPLETED'];
export type ConnState = 'reading' | 'streaming' | 'reconnecting' | 'disconnected';

export function terminalNotice(status: GenerationJob['status']) {
  switch (status) {
    case 'FAILED': return { tone: 'bg-rose-50 text-rose-800', text: '任务失败，失败结果不会冒充已完成。可返回重新检查规格并启动新任务。' };
    case 'PARTIAL_FAILED': return { tone: 'bg-rose-50 text-rose-800', text: '部分题目检查失败，其余题目可以查看，但整卷不视为完成，也不可发布。' };
    case 'RECONCILING': return { tone: 'bg-amber-50 text-amber-800', text: '外部调用结果尚未核实，已停止继续生成，请先对账，不再自动重发计费请求。' };
    case 'CANCELLED': return { tone: 'bg-slate-100 text-slate-600', text: '任务已取消，迟到的结果不会写入当前试卷。' };
    default: return null;
  }
}
