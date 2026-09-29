"""Persist bounded, non-content diagnostics for failed slots."""
import re
from services.exam.job_contracts import _now


def record_failure(repo, exam_id, job_id, slot_id, exc):
    current = repo.get(exam_id)
    if not (current and current['job_id'] == job_id and current['status'] == 'RUNNING'):
        return False
    status = getattr(exc, 'status', None)
    raw = str(exc)
    # Only adapter-owned codes; never persist arbitrary exception text/model output.
    code = raw if re.fullmatch(r'HERMES_[A-Z_]+(?::[A-Za-z0-9_./-]+)*', raw) else 'GENERATION_ERROR'
    known = {
        'PLAN_TOPIC_UNRESOLVED': ('PLAN_TOPIC_UNRESOLVED', '旧计划未绑定具体考点，请重新预览并确认题槽计划'),
        'Blind output must contain only short verifiable steps': ('BLIND_STEPS_INVALID', '盲解步骤字段不合法或摘要长度超限'),
        'Candidate local_id differs from its frozen slot': ('CANDIDATE_ID_MISMATCH', '题目编号与冻结题槽不一致'),
        'Blind output has no structured answer': ('BLIND_ANSWER_INVALID', '盲解缺少结构化答案'),
        'Blind option IDs must be strings': ('BLIND_OPTIONS_INVALID', '盲解选项标识不是字符串'),
    }
    message = '生成输出格式校验失败'  if code.startswith('HERMES_OUTPUT_INVALID') else '生成调用未正常完成'
    code, message = known.get(raw, (code, message))
    phase = getattr(exc, 'phase', None) or ('solver' if code.startswith('BLIND_') else 'unknown')
    diagnostic = {'code': code[:500], 'phase': phase,
                  'message': message, 'exception_type': type(exc).__name__}
    for slot in current['slots']:
        if slot['slot_id'] == slot_id:
            slot['failure'] = diagnostic
            if status == 'FAILED':
                slot['status'] = 'FAIL'
    current['logs'].append({'timestamp': _now(), 'slot_id': slot_id, 'role': 'system',
                            'level': 'error', 'message': message, 'diagnostic': diagnostic})
    current['completed_slots'] = sum(s['status'] in {'READY', 'REVIEW_REQUIRED', 'FAIL'} for s in current['slots'])
    if status != 'FAILED':
        current['status'] = 'FAILED' if status == 'BUDGET_EXCEEDED' else 'RECONCILING'
    repo.replace(current, current['version'])
    return status == 'FAILED'
