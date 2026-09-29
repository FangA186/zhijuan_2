from __future__ import annotations
import random
from typing import Any


def _build_solution(
    local_id: str, order_num: int, topic: str, score_x100: int, rng: random.Random
) -> dict[str, Any]:
    """Build authentic multi-part comprehensive solution question with scoring rubric."""
    t = topic
    score_points = score_x100 // 100
    part1_score = score_points // 2
    part2_score = score_points - part1_score

    if any(k in t for k in ("三角", "解三角形", "正弦定理", "余弦定理")):
        prompt_text = (
            r"在 $\triangle ABC$ 中，内角 $A, B, C$ 所对的边分别为 $a, b, c$，已知 $2b\cos A = c\cos A + a\cos C$。"
            rf"\n(1) 求角 $A$ 的大小；（{part1_score}分）"
            rf"\n(2) 若 $a = \sqrt{7}$，$b = 2$，求 $\triangle ABC$ 的面积。（{part2_score}分）"
        )
        explanation = (
            r"【详细解析与解题步骤】"
            r"\n(1) 由正弦定理，原式可化为 $2\sin B\cos A = \sin C\cos A + \sin A\cos C$；"
            r"\n又 $\sin C\cos A + \sin A\cos C = \sin(A + C) = \sin B$；"
            r"\n因为在 $\triangle ABC$ 中 $\sin B \ne 0$，所以两边同除以 $\sin B$ 得 $2\cos A = 1 \implies \cos A = \frac{1}{2}$；"
            r"\n因为 $A \in (0, \pi)$，所以 $A = \frac{\pi}{3}$。"
            r"\n"
            r"\n(2) 由余弦定理 $a^2 = b^2 + c^2 - 2bc\cos A$，"
            r"\n代入数据得 $7 = 4 + c^2 - 2 \times 2 \times c \times \frac{1}{2} \implies c^2 - 2c - 3 = 0$；"
            r"\n解得 $c = 3$（负根 $c = -1$ 舍去）；"
            r"\n所以 $S_{\triangle ABC} = \frac{1}{2}bc\sin A = \frac{1}{2} \times 2 \times 3 \times \sin\frac{\pi}{3} = \frac{3\sqrt{3}}{2}$。"
        )
        rubrics = [
            {
                "step": 1,
                "criterion": r"利用正弦定理角化边并利用两角和正弦公式求出 $\cos A = \frac{1}{2}$，得出 $A = \frac{\pi}{3}$",
                "score_x100": part1_score * 100,
            },
            {
                "step": 2,
                "criterion": r"建立余弦定理方程 $7 = 4 + c^2 - 2c$，因式分解求出边长 $c = 3$",
                "score_x100": (part2_score // 2) * 100,
            },
            {
                "step": 3,
                "criterion": r"应用三角形面积公式 $S = \frac{1}{2}bc\sin A$ 准确求得面积 $\frac{3\sqrt{3}}{2}$",
                "score_x100": (part2_score - part2_score // 2) * 100,
            },
        ]
    elif any(k in t for k in ("函数", "单调", "最值", "导数", "解析式")):
        prompt_text = (
            rf"已知函数 $f(x) = x^2 - 2ax + 3$ ($a \in \mathbf{{R}}$) 考查【{topic}】。"
            rf"\n(1) 当 $a = 2$ 时，求不等式 $f(x) \le 0$ 的解集；（{part1_score}分）"
            rf"\n(2) 若对任意 $x \in [1, 3]$，都有 $f(x) \ge 0$ 恒成立，求实数 $a$ 的取值范围。（{part2_score}分）"
        )
        explanation = (
            r"【详细解析与解题步骤】"
            r"\n(1) 当 $a = 2$ 时，$f(x) = x^2 - 4x + 3 = (x-1)(x-3)$；"
            r"\n由 $f(x) \le 0$ 得 $(x-1)(x-3) \le 0$，解得 $1 \le x \le 3$；"
            r"\n所以不等式的解集为 $\{x \mid 1 \le x \le 3\}$。"
            r"\n"
            r"\n(2) 函数图象为开口向上的抛物线，对称轴为直线 $x = a$。"
            r"\n① 当 $a < 1$ 时，$f(x)$ 在 $[1, 3]$ 上单调递增，最小值为 $f(1) = 4 - 2a \ge 0 \implies a \le 2$；结合 $a < 1$ 得 $a < 1$；"
            r"\n② 当 $1 \le a \le 3$ 时，最小值为顶点纵坐标 $f(a) = 3 - a^2 \ge 0 \implies a^2 \le 3 \implies -\sqrt{3} \le a \le \sqrt{3}$；结合 $1 \le a \le 3$ 得 $1 \le a \le \sqrt{3}$；"
            r"\n③ 当 $a > 3$ 时，$f(x)$ 在 $[1, 3]$ 上单调递减，最小值为 $f(3) = 12 - 6a \ge 0 \implies a \le 2$，与 $a > 3$ 矛盾，无解；"
            r"\n综上所述，实数 $a$ 的取值范围为 $(-\infty, \sqrt{3}]$。"
        )
        rubrics = [
            {
                "step": 1,
                "criterion": r"正确因式分解并求出 $a=2$ 时的不等式解集 $\{x \mid 1 \le x \le 3\}$",
                "score_x100": part1_score * 100,
            },
            {
                "step": 2,
                "criterion": r"找出抛物线对称轴 $x = a$，展开针对区间 $[1, 3]$ 的三分类讨论",
                "score_x100": (part2_score // 2) * 100,
            },
            {
                "step": 3,
                "criterion": r"分别求解各情况不等式并取并集，得出参数范围 $(-\infty, \sqrt{3}]$",
                "score_x100": (part2_score - part2_score // 2) * 100,
            },
        ]
    else:
        prompt_text = (
            rf"已知关于 $x$ 的函数 $f(x) = ax^2 - (2a+1)x + 2$ ($a \in \mathbf{{R}}$) 考查【{topic}】。"
            rf"\n(1) 当 $a = 1$ 时，求函数 $f(x)$ 的零点；（{part1_score}分）"
            rf"\n(2) 解关于 $x$ 的不等式 $f(x) > 0$。（{part2_score}分）"
        )
        explanation = (
            r"【详细解析与解题步骤】"
            r"\n(1) 当 $a = 1$ 时，$f(x) = x^2 - 3x + 2 = (x-1)(x-2)$；"
            r"\n令 $f(x) = 0$，解得 $x_1 = 1, x_2 = 2$。所以函数 $f(x)$ 的零点为 $1$ 和 $2$。"
            r"\n"
            r"\n(2) 原不等式可因式分解为 $(ax - 1)(x - 2) > 0$。"
            r"\n① 当 $a = 0$ 时，不等式化为 $-(x - 2) > 0 \implies x < 2$；"
            r"\n② 当 $a > 0$ 时，原式等价于 $(x - \frac{1}{a})(x - 2) > 0$；"
            r"\n  若 $\frac{1}{a} > 2 \iff 0 < a < \frac{1}{2}$，解集为 $(-\infty, 2) \cup (\frac{1}{a}, +\infty)$；"
            r"\n  若 $\frac{1}{a} = 2 \iff a = \frac{1}{2}$，解集为 $\{x \mid x \ne 2\}$；"
            r"\n  若 $\frac{1}{a} < 2 \iff a > \frac{1}{2}$，解集为 $(-\infty, \frac{1}{a}) \cup (2, +\infty)$；"
            r"\n③ 当 $a < 0$ 时，原式等价于 $(x - \frac{1}{a})(x - 2) < 0$，解集为 $(\frac{1}{a}, 2)$。"
        )
        rubrics = [
            {
                "step": 1,
                "criterion": r"因式分解求出 $a=1$ 时的零点 $x_1 = 1, x_2 = 2$",
                "score_x100": part1_score * 100,
            },
            {
                "step": 2,
                "criterion": r"将不等式化为 $(ax - 1)(x - 2) > 0$，讨论 $a=0$ 及 $a<0$ 的情况",
                "score_x100": (part2_score // 2) * 100,
            },
            {
                "step": 3,
                "criterion": r"针对 $a > 0$ 比较两根 $\frac{1}{a}$ 与 $2$ 的大小，完整写出综合解集",
                "score_x100": (part2_score - part2_score // 2) * 100,
            },
        ]

    return {
        "public": {
            "local_id": local_id,
            "kind": "solution",
            "prompt": [{"type": "text", "text": prompt_text}],
            "options": [],
            "score_x100": score_x100,
            "material_ids": [],
            "children": [],
            "answer_space_lines": 12,
        },
        "private": {
            "answers": [
                {
                    "local_question_id": local_id,
                    "answer_kind": "rubric",
                    "correct_option_ids": [],
                    "answer_text": "详细解答及推导步骤见下方解析与采分点",
                    "solution": [{"type": "text", "text": explanation}],
                    "explanation": [{"type": "text", "text": explanation}],
                    "scoring_rubric": rubrics,
                    "rubric": [
                        {"id": f"r{r['step']}", "description": r["criterion"], "score_x100": r["score_x100"], "acceptable_variants": []}
                        for r in rubrics
                    ],
                }
            ]
        },
    }

