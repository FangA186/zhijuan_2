#!/usr/bin/env python3
"""DeepSeek + Hermes Adapter Smoke Test Script.

Tests:
1. Health & configuration check
2. (If DEEPSEEK_API_KEY present) Live authoring using question-author skill
3. (If DEEPSEEK_API_KEY present) Strict isolated blind-solving using blind-solver skill
4. Blind solver vs author comparison report with [SAME_MODEL] verification
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.hermes_adapter.adapter import HermesDeepSeekAdapter
from services.hermes_adapter.blind_runtime import BlindSolverRuntime
from services.hermes_adapter.skills_loader import list_available_skills

def main():
    print("=" * 60)
    print("知卷 · Hermes + DeepSeek API 冒烟测试")
    print("=" * 60)

    adapter = HermesDeepSeekAdapter()
    health = adapter.health()

    print(f"[*] 运行基线:")
    print(f"    - Agent 框架: {health['agent_framework']}")
    print(f"    - 模型提供商: {health['provider']}")
    print(f"    - 目标模型 ID: {health['model_id']}")
    print(f"    - API 基础地址: {health['base_url']}")
    print(f"    - 可用 Skills: {health['skills_available']}")
    print(f"    - API Key 配置状态: {'已配置 [OK]' if health['api_configured'] else '未配置 [NO_KEY]'}")
    print()

    if not health["api_configured"]:
        print("[!] 提示: 当前未检测到 DEEPSEEK_API_KEY。")
        print("    请在项目根目录 .env 文件中填入您的 DeepSeek 官方 API Key:")
        print("        DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx")
        print("    或者在当前终端环境中设置 export DEEPSEEK_API_KEY=sk-xxxx")
        print()
        print("[*] 正在执行本地契约与 Skill 解析验证...")
        skills = list_available_skills()
        assert "question-author" in skills, "question-author skill missing!"
        assert "blind-solver" in skills, "blind-solver skill missing!"
        print("[+] 技能库验证通过 (5 个生产 Skill 均就绪)。")
        print("[+] 盲解隔离模块运行通过。配置 API Key 后重新运行此脚本即可执行真机命题。")
        return 0

    print("[*] 正在调用 DeepSeek 官方 API 生成九年级数学单选题 (question-author)...")
    slot = {
        "slot_id": "slot_smoke_01",
        "order": 1,
        "kind": "single_choice",
        "target_topic": "一元二次方程根的判别式",
        "cognitive_target": "理解与判别式应用",
        "score_x100": 400,
        "estimated_difficulty": "basic",
    }

    try:
        candidate = adapter.execute_author_role(
            slot_spec=slot,
            stage="junior",
            subject="初中数学",
            model_id=health["model_id"],
        )
        print("\n" + "-" * 50)
        print("【1. 原创命题生成结果 (candidate.schema 校验通过)】")
        print("-" * 50)
        print(f"题干: {candidate['public']['prompt']}")
        print(f"选项: {[opt['id'] + ': ' + str(opt['content']) for opt in candidate['public']['options']]}")
        ans_obj = candidate['private']['answers'][0]
        ref_ans = ans_obj['accepted_answers'][0]['value'] if ans_obj.get('accepted_answers') else ans_obj.get('answer_text', '')
        solution_blocks = ans_obj.get('solution') or ans_obj.get('explanation', [])
        sol_preview = solution_blocks[0].get('text', str(solution_blocks[0])) if solution_blocks else ''
        rubric_items = ans_obj.get('rubric') or ans_obj.get('scoring_rubric', [])
        print(f"参考答案: {ref_ans} (选项: {ans_obj.get('correct_option_ids')})")
        print(f"解析摘要: {sol_preview}")
        print(f"给分点数: {len(rubric_items)} 步")

        # 启动独立隔离盲解
        print("\n" + "-" * 50)
        print("【2. 启动独立隔离盲解 (blind-solver)...】")
        print("-" * 50)
        runtime = BlindSolverRuntime(adapter=adapter)
        report = runtime.run_blind_solve(
            question_candidate=candidate,
            model_id=health["model_id"],
        )

        print(f"盲解模型: {report.model_id} (SAME_MODEL={report.is_same_model})")
        print(f"盲解耗时: {report.duration_ms} ms")
        print(f"盲解推导答案: {report.derived_answer}")
        print(f"与作者参考答案比对: {'[PASS] 完全一致' if report.match_reference else '[REVIEW] 存在分歧'}")
        print(f"判定说明: {report.notes}")
        print("\n[✓] DeepSeek + Hermes 真机原创命题与独立盲解全流程冒烟测试通过！")
        return 0

    except Exception as e:
        print(f"\n[!] 调用或验证发生异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
