from __future__ import annotations
import random
from typing import Any


def _build_multiple_choice(
    local_id: str, order_num: int, topic: str, score_x100: int, rng: random.Random
) -> dict[str, Any]:
    """Build authentic multiple-choice question for New Gaokao (2~4 correct options)."""
    t = topic
    if any(k in t for k in ("三角", "正弦", "余弦", "图像", "变换")):
        prompt_text = (
            r"已知函数 $f(x) = 2\sin(2x + \frac{\pi}{3})$，则下列说法正确的有（　）"
        )
        raw_options = [
            ("opt_A", r"$f(x)$ 的最小正周期为 $\pi$"),
            ("opt_B", r"$f(x)$ 的图象关于直线 $x = \frac{\pi}{12}$ 对称"),
            ("opt_C", r"$f(x)$ 在区间 $[0, \frac{\pi}{3}]$ 上的最大值为 $2$"),
            ("opt_D", r"$f(x)$ 的图象关于点 $(-\frac{\pi}{6}, 0)$ 对称"),
        ]
        correct_ids = ["opt_A", "opt_B", "opt_C", "opt_D"]
        ans_chars = ["A", "B", "C", "D"]
        explanation = (
            r"对于 A：$T = \frac{2\pi}{\omega} = \frac{2\pi}{2} = \pi$，A 正确；"
            r"对于 B：当 $x = \frac{\pi}{12}$ 时，$2x + \frac{\pi}{3} = \frac{\pi}{6} + \frac{\pi}{3} = \frac{\pi}{2}$，取最大值 $2$，故为对称轴，B 正确；"
            r"对于 C：当 $x \in [0, \frac{\pi}{3}]$ 时，$2x + \frac{\pi}{3} \in [\frac{\pi}{3}, \pi]$，正弦最大值为 $1$（在 $\frac{\pi}{2}$ 处取得），故最大值为 $2$，C 正确；"
            r"对于 D：当 $x = -\frac{\pi}{6}$ 时，$2x + \frac{\pi}{3} = 0$，$f(-\frac{\pi}{6}) = 0$，故图象关于该点对称，D 正确。"
            r"综上，全选 ABCD。"
        )
    elif any(k in t for k in ("不等式", "基本不等式", "性质")):
        prompt_text = (
            r"已知实数 $a, b, c$ 满足 $a > b > 0$，则下列不等式恒成立的有（　）"
        )
        raw_options = [
            ("opt_A", r"$\frac{1}{a} < \frac{1}{b}$"),
            ("opt_B", r"$a^2 > b^2$"),
            ("opt_C", r"$\frac{b}{a} < \frac{b+1}{a+1}$"),
            ("opt_D", r"$ac^2 > bc^2$"),
        ]
        correct_ids = ["opt_A", "opt_B", "opt_C"]
        ans_chars = ["A", "B", "C"]
        explanation = (
            r"对于 A：$a > b > 0$ 时倒数反向，$\frac{1}{a} < \frac{1}{b}$ 成立，A 正确；"
            r"对于 B：同为正数且 $a > b$，两边平方得 $a^2 > b^2$，B 正确；"
            r"对于 C：糖水不等式原理，$\frac{b+1}{a+1} - \frac{b}{a} = \frac{a(b+1) - b(a+1)}{a(a+1)} = \frac{a - b}{a(a+1)} > 0$，C 正确；"
            r"对于 D：当 $c = 0$ 时 $ac^2 = bc^2 = 0$，不等号不成立，D 错误。"
            r"故选 ABC。"
        )
    else:
        prompt_text = (
            rf"已知定义在 $\mathbf{{R}}$ 上的函数 $f(x)$ 考查【{topic}】，"
            r"满足 $f(x + 2) = -f(x)$，且当 $x \in [0, 2]$ 时，$f(x) = x(2 - x)$，则下列结论正确的有（　）"
        )
        raw_options = [
            ("opt_A", r"$f(x)$ 是周期为 $4$ 的周期函数"),
            ("opt_B", r"$f(x)$ 的图象关于点 $(2, 0)$ 对称"),
            ("opt_C", r"$f(x)$ 在 $[0, 1]$ 上单调递增"),
            ("opt_D", r"$f(2026) = 0$"),
        ]
        correct_ids = ["opt_A", "opt_B", "opt_C", "opt_D"]
        ans_chars = ["A", "B", "C", "D"]
        explanation = (
            r"对于 A：$f(x + 4) = -f(x + 2) = f(x)$，故周期为 $4$，A 正确；"
            r"对于 B：由 $f(x + 2) = -f(x)$，代入 $x=0$ 得 $f(2) = 0$，且 $f(2 + x) = -f(x) = -f(2 - x)$，B 正确；"
            r"对于 C：当 $x \in [0, 2]$ 时，$f(x) = -(x-1)^2 + 1$，对称轴为 $x=1$，在 $[0, 1]$ 上递增，C 正确；"
            r"对于 D：$2026 = 4 \times 506 + 2$，所以 $f(2026) = f(2) = 0$，D 正确。"
            r"故选 ABCD。"
        )

    options = [
        {"id": opt_id, "content": [{"type": "text", "text": opt_text}]}
        for opt_id, opt_text in raw_options
    ]
    ans_str = ", ".join(ans_chars)

    return {
        "public": {
            "local_id": local_id,
            "kind": "multiple_choice",
            "prompt": [{"type": "text", "text": prompt_text}],
            "options": options,
            "score_x100": score_x100,
            "material_ids": [],
            "children": [],
            "answer_space_lines": 0,
        },
        "private": {
            "answers": [
                {
                    "local_question_id": local_id,
                    "answer_kind": "selection",
                    "correct_option_ids": correct_ids,
                    "answer_text": ans_str,
                    "accepted_answers": [{"value": ans_str, "format": "text", "conditions": "全部正确选项"}],
                    "solution": [{"type": "text", "text": explanation}],
                    "explanation": [{"type": "text", "text": explanation}],
                    "rubric": [
                        {"id": "r1", "description": f"全部选对得满分 ({score_x100/100:g}分)，部分选对得部分分，有选错得 0 分", "score_x100": score_x100, "acceptable_variants": [ans_str]}
                    ],
                }
            ]
        },
    }

