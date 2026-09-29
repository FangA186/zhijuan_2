"""Selection tiers are exclusive; solution rubric points are additive."""
import re

SELECTION_KINDS = {'single_choice', 'multiple_choice', 'true_false'}


def scoring_errors(question, answer, spec):
    mode = answer.get('scoring_mode', 'additive')
    rubric = answer['rubric']
    if question['kind'] in SELECTION_KINDS and 'multiple_choice_partial_score_x100' in spec and mode != 'exclusive':
        return ['当前规格要求选择题使用互斥评分，模型不能改为累加模式']
    if mode == 'exclusive':
        if question['kind'] not in SELECTION_KINDS or rubric:
            return ['互斥档位仅用于选择/判断题，不能同时填写累加采分点']
        expected = spec.get('multiple_choice_partial_score_x100', 0) if question['kind'] == 'multiple_choice' else 0
        partial = answer.get('partial_score_x100')
        if partial != expected or not isinstance(partial, int) or isinstance(partial, bool) or not 0 <= partial < question['score_x100']:
            return ['少选得分必须等于教师设定，且小于本题满分']
        return []
    if answer.get('partial_score_x100', 0) != 0:
        return ['累加模式不能同时设置少选得分']
    if sum(r['score_x100'] for r in rubric) != question['score_x100']:
        return ['累加采分点合计与本题满分不一致']
    return []


def answer_text_conflicts(question, answer):
    """Check explicit answer declarations, never guess the answer from free prose."""
    if question['kind'] not in SELECTION_KINDS:
        return []
    labels = {chr(65+i): option['id'] for i, option in enumerate(question['options'])}
    expected = set(answer['correct_option_ids'])
    texts = [r['description'] for r in answer['rubric']]
    texts += [b['text'] for b in answer['solution'] if b['type'] == 'text']
    declaration = r'(?:正确选项(?:为|是|[:：])|正确答案(?:为|是|[:：])|全部选对[（(]|答案(?:为|是|[:：]))\s*([A-Z](?:[、,，及和\s]*[A-Z])*)\s*(?=$|[。；;）)])'
    for text in texts:
        for match in re.finditer(declaration, text):
            if text[match.end():].lstrip().startswith(('=', '<', '>')):
                continue
            letters = re.findall(r'[A-Z]', match.group(1))
            if letters and all(letter in labels for letter in letters):
                if {labels[letter] for letter in letters} != expected:
                    return ['答案说明中声明的正确选项与结构化答案不一致；需修订，不能自动选取一份作为正确答案']
    return []
