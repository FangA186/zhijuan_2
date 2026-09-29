export interface DiagnosticSlot { slot_id: string; status: string; question_revision_id?: string; failure_code?: string;
  failure?: { code: string; phase: string; message: string } }
interface Check { rule_id: string; status: string; evidence_summary?: string; }
export interface SlotValidation {
  revision?: { question_revision_id?: string };
  rule_checks: Check[];
  blind_evidence?: { match_reference?: boolean; is_same_model?: boolean };
}
interface CandidateShape {
  public: { local_id: string; kind: string };
  private: { answers: { local_question_id: string; correct_option_ids?: string[] }[] };
}
const RULES: Record<string, string> = {
  ANSWER_TEXT_CONSISTENCY: '答案说明中声明的选项与结构化答案冲突，需修订后重新检查',
  STRUCTURE: '题目字段或格式不符合约定', ANSWER_AND_RUBRIC: '答案引用、正确选项数量或评分合计不符合规则',
  SLOT: '题型、分值或材料与题槽要求不一致', ASSET_INTEGRITY: '配图缺失、损坏或来源未验证',
  MATH_TRUTH: '缺少可信数学证明，正确性仍需教师核对',
};
export function slotReasons(slot: DiagnosticSlot, jobId: string,
  records: Record<string, SlotValidation>, candidates: CandidateShape[]): string[] {
  const entry = Object.entries(records).find(([, record]) => record.revision?.question_revision_id === (slot.question_revision_id || `${jobId}:${slot.slot_id}`));
  if (!entry) {
    if (slot.failure) {
      const phase = slot.failure.phase === 'author' ? '命题' : slot.failure.phase === 'solver' ? '盲解' : '生成';
      return [`${phase}阶段：${slot.failure.message}。`, `诊断：${slot.failure.code}`];
    }
    if (slot.failure_code === 'HERMES_OUTPUT_INVALID') return ['生成输出格式不符合约定；该题未进入后续检查。'];
    return ['FAIL', 'REVIEW_REQUIRED'].includes(slot.status)
      ? ['未找到绑定本题的检查记录；旧日志未保存逐题异常细节，无法确定具体失败字段或阶段。'] : [];
  }
  const [localId, record] = entry;
  return record.rule_checks.filter(check => check.status !== 'PASS').map(check => {
    if (check.rule_id === 'IN_PAPER_DIVERSITY') return check.evidence_summary || '同卷重复情况需要复核';
    if (check.rule_id === 'AGENT_REVIEW') return `审核意见：${check.evidence_summary || '待人工复核'}`;
    if (check.rule_id === 'BLIND_COMPARISON') {
      const blind = record.blind_evidence;
      if (!blind) return '未获得盲解比对结果，不能据此判断答案正确。';
      return `${blind.match_reference === true ? '盲解与参考答案一致' : blind.match_reference === false ? '盲解与参考答案不一致，需核对解答' : '盲解比对结果未知'}${blind.is_same_model ? '；使用同一模型，不构成独立正确性证明' : ''}。`;
    }
    if (check.rule_id === 'ANSWER_AND_RUBRIC') {
      if (check.evidence_summary && /少选|采分点|互斥|累加/.test(check.evidence_summary)) return check.evidence_summary;
      const candidate = candidates.find(c => c.public.local_id === localId);
      const answer = candidate?.private.answers.find(a => a.local_question_id === localId);
      if (candidate?.public.kind === 'multiple_choice' && answer && (answer.correct_option_ids?.length ?? 0) < 2)
        return `多选题只生成了 ${answer.correct_option_ids?.length ?? 0} 个正确选项，规则要求至少 2 个。`;
    }
    return `${RULES[check.rule_id] || '检查需要处理'}（${check.rule_id} · ${check.status}）`;
  });
}
