"""Planner contract and deterministic binding to teacher-owned slot structure."""
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator
from .topic_scope import GENERIC_TOPICS, AUXILIARY, CHAPTER

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / 'contracts/blueprint-design.schema.json').read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


def planning_input(spec, skeleton):
    return {'spec': spec, 'difficulty_quotas': skeleton['difficulty_distribution'],
            'slots': [{k: s[k] for k in ('slot_id', 'section_id', 'kind', 'score_x100')}
                      for s in skeleton['slots']], 'output_schema': SCHEMA,
            'instruction': '设计整卷，不生成题目答案。允许多考点综合；保持所有槽位编号、题型、分值及难度配额。'}


def bind_design(skeleton, design, provenance):
    errors = list(VALIDATOR.iter_errors(design))
    if errors:
        raise ValueError('规划输出格式错误：' + errors[0].message[:240])
    if design['conflicts']:
        raise ValueError('规划约束冲突：' + '；'.join(design['conflicts'])[:1000])
    slots = design['slots']
    expected = {s['slot_id']: s for s in skeleton['slots']}
    if len(slots) != len(expected) or {s['slot_id'] for s in slots} != set(expected):
        raise ValueError('规划题槽缺失、重复或新增')
    spec = skeleton['canonical_spec']
    sections = {s['id']: s for s in spec['sections']}
    if Counter(s['difficulty'] for s in slots) != Counter(skeleton['difficulty_distribution']):
        raise ValueError('规划难度题数不符合教师配置')
    briefs = set()
    result = copy.deepcopy(skeleton)
    chosen = {s['slot_id']: s for s in slots}
    for slot in result['slots']:
        item = chosen[slot['slot_id']]
        allowed = set(sections[slot['section_id']]['topics']) - set(spec['taught_scope']['excluded_topics'])
        topics = item['knowledge_ids']
        if not set(topics) <= allowed or set(topics) & GENERIC_TOPICS:
            raise ValueError(f"{slot['slot_id']} 的考点不在该题型批准范围内")
        if any(CHAPTER.match(t) or AUXILIARY.search(t) or t.startswith(('探究与发现', '数学建模 ')) for t in topics):
            raise ValueError(f"{slot['slot_id']} 应使用具体考点，不能直接以教材栏目为考点")
        brief = ''.join(item['design_brief'].split())
        if brief in briefs:
            raise ValueError('规划中存在重复的题目设计任务')
        briefs.add(brief)
        slot.update(target_topic='、'.join(topics), knowledge_ids=topics,
                    objective=item['cognitive_target'], cognitive_target=item['cognitive_target'],
                    estimated_difficulty=item['difficulty'], design_brief=item['design_brief'],
                    planning_rationale=item['rationale'])
        slot['constraints'] = [*spec['taught_scope']['permitted_methods'],
            *[f'排除：{t}' for t in spec['taught_scope']['excluded_topics']],
            '按 knowledge_ids 与 design_brief 命题，综合考查不越出已确认范围。']
    result.update(planning_summary=design['summary'], planning_source='hermes_planner', planner=provenance)
    fields = {'exam_id': result['exam_id'], 'spec_revision': result['spec_revision'],
              'plan_revision': result['plan_revision'], 'spec': spec, 'slots': result['slots']}
    result['plan_hash'] = hashlib.sha256(json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return result
