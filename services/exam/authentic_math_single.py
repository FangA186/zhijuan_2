from __future__ import annotations
import random
from typing import Any


def _build_single_choice(
    local_id: str, order_num: int, topic: str, score_x100: int, rng: random.Random
) -> dict[str, Any]:
    """Build authentic single-choice question with 4 LaTeX options."""
    t = topic
    if any(k in t for k in ("集合", "元素", "子集", "交集", "并集", "全集")):
        prompt_text = (
            r"已知全集 $U = \mathbf{R}$，集合 $A = \{x \in \mathbf{R} \mid x^2 - 3x - 4 \le 0\}$，"
            r"$B = \{x \in \mathbf{Z} \mid -1 \le x < 3\}$，则 $A \cap B =$（　）"
        )
        raw_options = [
            ("opt_A", r"$\{-1, 0, 1, 2\}$"),
            ("opt_B", r"$\{0, 1, 2\}$"),
            ("opt_C", r"$[-1, 3)$"),
            ("opt_D", r"$\{-1, 0, 1, 2, 3\}$"),
        ]
        correct_id = "opt_A"
        ans_char = "A"
        explanation = (
            r"由 $x^2 - 3x - 4 \le 0$ 可得 $(x-4)(x+1) \le 0$，解得 $-1 \le x \le 4$，即 $A = [-1, 4]$；"
            r"又 $B = \{x \in \mathbf{Z} \mid -1 \le x < 3\} = \{-1, 0, 1, 2\}$；"
            r"因此 $A \cap B = \{-1, 0, 1, 2\}$。故选 A。"
        )
    elif any(k in t for k in ("逻辑", "充分", "必要", "充要", "命题", "量词")):
        prompt_text = (
            r"设 $x \in \mathbf{R}$，则“$x > 2$”是“$x^2 - 4 > 0$”的（　）"
        )
        raw_options = [
            ("opt_A", r"充分不必要条件"),
            ("opt_B", r"必要不充分条件"),
            ("opt_C", r"充要条件"),
            ("opt_D", r"既不充分也不必要条件"),
        ]
        correct_id = "opt_A"
        ans_char = "A"
        explanation = (
            r"若 $x > 2$，则 $x^2 > 4$，即 $x^2 - 4 > 0$ 恒成立，满足充分性；"
            r"反之，若 $x^2 - 4 > 0$，解得 $x > 2$ 或 $x < -2$，推不出 $x > 2$，不满足必要性；"
            r"所以“$x > 2$”是“$x^2 - 4 > 0$”的充分不必要条件。故选 A。"
        )
    elif any(k in t for k in ("基本不等式", "不等式", "判别式", "根的判别式", "均值")):
        prompt_text = (
            r"已知正实数 $x, y$ 满足 $x + 2y = 4$，则 $xy$ 的最大值为（　）"
        )
        raw_options = [
            ("opt_A", r"$2$"),
            ("opt_B", r"$4$"),
            ("opt_C", r"$\sqrt{2}$"),
            ("opt_D", r"$8$"),
        ]
        correct_id = "opt_A"
        ans_char = "A"
        explanation = (
            r"因为 $x > 0, y > 0$，由均值不等式 $x + 2y \ge 2\sqrt{2xy}$，"
            r"代入 $x + 2y = 4$ 得 $4 \ge 2\sqrt{2xy}$，即 $\sqrt{2xy} \le 2$，"
            r"两边平方得 $2xy \le 4 \implies xy \le 2$。"
            r"当且仅当 $x = 2y = 2$，即 $x=2, y=1$ 时取等号。故选 A。"
        )
    elif any(k in t for k in ("单调", "奇偶", "对称", "周期", "最值", "函数性质", "函数概念")):
        prompt_text = (
            r"已知定义在 $\mathbf{R}$ 上的偶函数 $f(x)$ 在 $[0, +\infty)$ 上单调递增，"
            r"若 $f(2) = 1$，则满足不等式 $f(x - 1) < 1$ 的 $x$ 的取值范围是（　）"
        )
        raw_options = [
            ("opt_A", r"$(-1, 3)$"),
            ("opt_B", r"$(1, 3)$"),
            ("opt_C", r"$(-\infty, -1) \cup (3, +\infty)$"),
            ("opt_D", r"$(-3, 1)$"),
        ]
        correct_id = "opt_A"
        ans_char = "A"
        explanation = (
            r"因为 $f(x)$ 为偶函数，所以 $f(x - 1) = f(|x - 1|)$；"
            r"又 $f(x)$ 在 $[0, +\infty)$ 上单调递增，且 $f(2) = 1$；"
            r"由 $f(|x - 1|) < f(2)$ 可得 $|x - 1| < 2$，解得 $-2 < x - 1 < 2 \implies -1 < x < 3$。"
            r"故选 A。"
        )
    elif any(k in t for k in ("指数", "对数", "幂函数")):
        prompt_text = (
            r"设 $a = 2^{0.3}$，$b = \log_2 3$，$c = \log_3 2$，则 $a, b, c$ 的大小关系为（　）"
        )
        raw_options = [
            ("opt_A", r"$b > a > c$"),
            ("opt_B", r"$a > b > c$"),
            ("opt_C", r"$b > c > a$"),
            ("opt_D", r"$c > a > b$"),
        ]
        correct_id = "opt_A"
        ans_char = "A"
        explanation = (
            r"因为 $1 < a = 2^{0.3} < 2^{0.5} = \sqrt{2} \approx 1.414$；"
            r"而 $b = \log_2 3 > \log_2 2\sqrt{2} = 1.5$；"
            r"又 $0 < c = \log_3 2 < \log_3 3 = 1$；"
            r"所以 $b > a > c$。故选 A。"
        )
    elif any(k in t for k in ("三角", "正弦", "余弦", "正切", "诱导公式", "弧度")):
        prompt_text = (
            r"已知 $\sin(\alpha + \frac{\pi}{6}) = \frac{1}{3}$，则 $\cos(\frac{\pi}{3} - 2\alpha) =$（　）"
        )
        raw_options = [
            ("opt_A", r"$-\frac{7}{9}$"),
            ("opt_B", r"$\frac{7}{9}$"),
            ("opt_C", r"$-\frac{8}{9}$"),
            ("opt_D", r"$\frac{8}{9}$"),
        ]
        correct_id = "opt_A"
        ans_char = "A"
        explanation = (
            r"因为 $\cos(\frac{\pi}{3} - 2\alpha) = 1 - 2\sin^2(\frac{\pi}{6} - \alpha)$，由诱导公式变换知其等于 "
            r"$2\sin^2(\alpha + \frac{\pi}{6}) - 1 = 2 \times (\frac{1}{3})^2 - 1 = \frac{2}{9} - 1 = -\frac{7}{9}$。故选 A。"
        )
    else:
        prompt_text = (
            rf"已知关于 $x$ 的方程 $x^2 - 2x + m = 0$ 考查【{topic}】，"
            r"若方程有两个不相等的实数根 $x_1, x_2$，且满足 $x_1^2 + x_2^2 = 6$，则实数 $m$ 的值为（　）"
        )
        raw_options = [
            ("opt_A", r"$-1$"),
            ("opt_B", r"$1$"),
            ("opt_C", r"$-2$"),
            ("opt_D", r"$2$"),
        ]
        correct_id = "opt_A"
        ans_char = "A"
        explanation = (
            r"由韦达定理得 $x_1 + x_2 = 2$，$x_1 x_2 = m$；"
            r"由 $x_1^2 + x_2^2 = (x_1 + x_2)^2 - 2x_1 x_2 = 4 - 2m = 6$，解得 $m = -1$；"
            r"验算判别式 $\Delta = (-2)^2 - 4(-1) = 8 > 0$，符合题意。故选 A。"
        )

    options = [
        {"id": opt_id, "content": [{"type": "text", "text": opt_text}]}
        for opt_id, opt_text in raw_options
    ]

    return {
        "public": {
            "local_id": local_id,
            "kind": "single_choice",
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
                    "correct_option_ids": [correct_id],
                    "answer_text": ans_char,
                    "accepted_answers": [{"value": ans_char, "format": "text", "conditions": "唯一正确选项"}],
                    "solution": [{"type": "text", "text": explanation}],
                    "explanation": [{"type": "text", "text": explanation}],
                    "rubric": [
                        {"id": "r1", "description": f"准确掌握【{topic}】并得出正解 {ans_char}", "score_x100": score_x100, "acceptable_variants": [ans_char]}
                    ],
                }
            ]
        },
    }

