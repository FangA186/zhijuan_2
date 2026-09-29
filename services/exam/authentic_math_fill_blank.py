from __future__ import annotations
import random
from typing import Any


def _build_fill_blank(
    local_id: str, order_num: int, topic: str, score_x100: int, rng: random.Random
) -> dict[str, Any]:
    """Build authentic fill-in-the-blank question."""
    t = topic
    if any(k in t for k in ("三角", "正弦", "余弦", "正切")):
        prompt_text = (
            r"已知 $\tan\alpha = 2$，则 $\frac{\sin\alpha + 2\cos\alpha}{2\sin\alpha - \cos\alpha} =$ ________。"
        )
        answer_val = r"\frac{4}{3}"
        display_val = "4/3"
        explanation = (
            r"由“弦化切”技巧，将分式的分子、分母同时除以 $\cos\alpha \ne 0$ 得："
            r"原式 $= \frac{\tan\alpha + 2}{2\tan\alpha - 1}$；"
            r"代入 $\tan\alpha = 2$ 计算：$\frac{2 + 2}{2 \times 2 - 1} = \frac{4}{3}$。"
        )
    elif any(k in t for k in ("幂函数", "指数", "对数")):
        prompt_text = (
            r"已知幂函数 $f(x) = (m^2 - m - 1)x^m$ 在 $(0, +\infty)$ 上单调递增，则实数 $m =$ ________。"
        )
        answer_val = "2"
        display_val = "2"
        explanation = (
            r"因为 $f(x)$ 为幂函数，所以其系数 $m^2 - m - 1 = 1$，解得 $m = 2$ 或 $m = -1$；"
            r"又函数在 $(0, +\infty)$ 上单调递增，指数需满足 $m > 0$，因此舍去 $m = -1$，得 $m = 2$。"
        )
    elif any(k in t for k in ("不等式", "解集", "判别式")):
        prompt_text = (
            r"若关于 $x$ 的不等式 $x^2 - 2x + a \le 0$ 的解集为 $[-1, 3]$，则实数 $a =$ ________。"
        )
        answer_val = "-3"
        display_val = "-3"
        explanation = (
            r"由题意可知 $-1$ 和 $3$ 是对应一元二次方程 $x^2 - 2x + a = 0$ 的两实数根；"
            r"根据根与系数的关系（韦达定理），$(-1) \times 3 = a \implies a = -3$。"
        )
    else:
        prompt_text = (
            rf"已知函数 $f(x) = \begin{{cases}} 2^x - 1, & x \le 1 \\ \log_2 x, & x > 1 \end{{cases}}$ 考查【{topic}】，"
            r"则 $f(f(4)) =$ ________。"
        )
        answer_val = "1"
        display_val = "1"
        explanation = (
            r"因为 $4 > 1$，代入对数段可得 $f(4) = \log_2 4 = 2$；"
            r"再求 $f(2)$：因为 $2 > 1$，继续代入对数段得 $f(2) = \log_2 2 = 1$；"
            r"所以 $f(f(4)) = 1$。"
        )

    return {
        "public": {
            "local_id": local_id,
            "kind": "fill_blank",
            "prompt": [{"type": "text", "text": prompt_text}],
            "options": [],
            "score_x100": score_x100,
            "material_ids": [],
            "children": [],
            "answer_space_lines": 2,
        },
        "private": {
            "answers": [
                {
                    "local_question_id": local_id,
                    "answer_kind": "expression",
                    "correct_option_ids": [],
                    "answer_text": display_val,
                    "accepted_answers": [
                        {"value": display_val, "format": "text", "conditions": "标准数值"},
                        {"value": answer_val, "format": "latex", "conditions": "LaTeX 表达式"},
                    ],
                    "solution": [{"type": "text", "text": explanation}],
                    "explanation": [{"type": "text", "text": explanation}],
                    "rubric": [
                        {"id": "r1", "description": f"填入正确答案 {display_val} 得满分", "score_x100": score_x100, "acceptable_variants": [display_val, answer_val]}
                    ],
                }
            ]
        },
    }

