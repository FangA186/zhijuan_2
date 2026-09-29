import { GeneratedCandidate } from '../types/candidate';

/**
 * 候选题目数据 GeneratedCandidates
 */
export const mockMathCandidates: GeneratedCandidate[] = [
  {
    public: {
      local_id: "slot_01",
      kind: "single_choice",
      prompt: [
        { type: "text", text: "若关于 $x$ 的一元二次方程 $x^2 - 4x + k = 0$ 有两个不相等的实数根，则实数 $k$ 的取值范围是（　　）" },
      ],
      options: [
        { id: "opt_A", label: "A", content: [{ type: "text", text: "$k < 4$" }] },
        { id: "opt_B", label: "B", content: [{ type: "text", text: "$k \\le 4$" }] },
        { id: "opt_C", label: "C", content: [{ type: "text", text: "$k > 4$" }] },
        { id: "opt_D", label: "D", content: [{ type: "text", text: "$k \\ge 4$" }] },
      ],
      score_x100: 400,
      material_ids: [],
      children: [],
      answer_space_lines: 2,
    },
    private: {
      answers: [
        {
          target_local_id: "slot_01",
          answer_text: "A",
          selected_option_ids: ["opt_A"],
          explanation: [
            { type: "text", text: "根据题意，方程有两个不相等的实数根，则根的判别式 $\\Delta > 0$。" },
            { type: "math", latex: "\\Delta = (-4)^2 - 4 \\times 1 \\times k = 16 - 4k > 0" },
            { type: "text", text: "解得 $4k < 16$，即 $k < 4$。故选 A。" },
          ],
          scoring_rubric: [
            { step: 1, score_x100: 200, criterion: "正确写出判别式 $\\Delta = 16 - 4k > 0$" },
            { step: 2, score_x100: 200, criterion: "正确求解不等式得到 $k < 4$ 并选出选项 A" },
          ],
        },
      ],
    },
  },
  {
    public: {
      local_id: "slot_02",
      kind: "single_choice",
      prompt: [
        { type: "text", text: "如图，在 $\\triangle ABC$ 中，$D$、$E$ 分别在 $AB$、$AC$ 边上，若 $DE \\parallel BC$，且 $\\frac{AD}{DB} = \\frac{2}{3}$，则 $\\frac{S_{\\triangle ADE}}{S_{\\triangle ABC}}$ 的值为（　　）" },
      ],
      options: [
        { id: "opt_A", label: "A", content: [{ type: "text", text: "$\\frac{2}{5}$" }] },
        { id: "opt_B", label: "B", content: [{ type: "text", text: "$\\frac{4}{9}$" }] },
        { id: "opt_C", label: "C", content: [{ type: "text", text: "$\\frac{4}{25}$" }] },
        { id: "opt_D", label: "D", content: [{ type: "text", text: "$\\frac{2}{3}$" }] },
      ],
      score_x100: 400,
      material_ids: [],
      children: [],
      answer_space_lines: 2,
    },
    private: {
      answers: [
        {
          target_local_id: "slot_02",
          answer_text: "C",
          selected_option_ids: ["opt_C"],
          explanation: [
            { type: "text", text: "∵ $\\frac{AD}{DB} = \\frac{2}{3}$，∴ $\\frac{AD}{AB} = \\frac{AD}{AD + DB} = \\frac{2}{2 + 3} = \\frac{2}{5}$。" },
            { type: "text", text: "∵ $DE \\parallel BC$，∴ $\\triangle ADE \\sim \\triangle ABC$。" },
            { type: "text", text: "相似三角形的面积比等于相似比的平方：" },
            { type: "math", latex: "\\frac{S_{\\triangle ADE}}{S_{\\triangle ABC}} = \\left(\\frac{AD}{AB}\\right)^2 = \\left(\\frac{2}{5}\\right)^2 = \\frac{4}{25}" },
            { type: "text", text: "故选 C。" },
          ],
          scoring_rubric: [
            { step: 1, score_x100: 200, criterion: "求得相似比 $\\frac{AD}{AB} = \\frac{2}{5}$" },
            { step: 2, score_x100: 200, criterion: "应用面积比等于相似比平方得出 $\\frac{4}{25}$ 并选 C" },
          ],
        },
      ],
    },
  },
  {
    public: {
      local_id: "slot_03",
      kind: "single_choice",
      prompt: [
        { type: "text", text: "已知 $x_1, x_2$ 是一元二次方程 $x^2 - 3x - 1 = 0$ 的两个实数根，则代数式 $x_1^2 + x_2^2$ 的值为（　　）" },
      ],
      options: [
        { id: "opt_A", label: "A", content: [{ type: "text", text: "$7$" }] },
        { id: "opt_B", label: "B", content: [{ type: "text", text: "$11$" }] },
        { id: "opt_C", label: "C", content: [{ type: "text", text: "$-7$" }] },
        { id: "opt_D", label: "D", content: [{ type: "text", text: "$10$" }] },
      ],
      score_x100: 400,
      material_ids: [],
      children: [],
      answer_space_lines: 2,
    },
    private: {
      answers: [
        {
          target_local_id: "slot_03",
          answer_text: "B",
          selected_option_ids: ["opt_B"],
          explanation: [
            { type: "text", text: "由韦达定理（根与系数关系）可得：" },
            { type: "math", latex: "x_1 + x_2 = 3,\\quad x_1 x_2 = -1" },
            { type: "text", text: "根据完全平方公式变形：" },
            { type: "math", latex: "x_1^2 + x_2^2 = (x_1 + x_2)^2 - 2x_1 x_2 = 3^2 - 2 \\times (-1) = 9 + 2 = 11" },
            { type: "text", text: "故选 B。" },
          ],
          scoring_rubric: [
            { step: 1, score_x100: 200, criterion: "正确应用韦达定理写出 $x_1+x_2=3, x_1 x_2=-1$" },
            { step: 2, score_x100: 200, criterion: "代数式恒等变形求得结果 11 并选 B" },
          ],
        },
      ],
    },
  },
  {
    public: {
      local_id: "slot_08",
      kind: "solution",
      prompt: [
        { type: "text", text: "已知关于 $x$ 的一元二次方程 $x^2 - (2m+1)x + m^2 + m = 0$。\n(1) 求证：无论 $m$ 取何实数，该方程总有两个不相等的实数根；\n(2) 若该方程的两个实数根满足 $x_1^2 + x_2^2 = 13$，求实数 $m$ 的值。" },
      ],
      options: [],
      score_x100: 1800,
      material_ids: [],
      children: [],
      answer_space_lines: 8,
    },
    private: {
      answers: [
        {
          target_local_id: "slot_08",
          answer_text: "(1) 证明略；(2) m = 2 或 m = -3",
          explanation: [
            { type: "text", text: "【解析】\n(1) 证明：计算判别式 $\\Delta$：" },
            { type: "math", latex: "\\Delta = [-(2m+1)]^2 - 4 \\times 1 \\times (m^2 + m) = 4m^2 + 4m + 1 - 4m^2 - 4m = 1" },
            { type: "text", text: "∵ $\\Delta = 1 > 0$ 恒成立，∴ 无论 $m$ 取何实数，该方程总有两个不相等的实数根。\n\n(2) 解：由根与系数的关系可得：" },
            { type: "math", latex: "x_1 + x_2 = 2m+1,\\quad x_1 x_2 = m^2 + m" },
            { type: "text", text: "∵ $x_1^2 + x_2^2 = (x_1 + x_2)^2 - 2x_1 x_2 = 13$，代入得：" },
            { type: "math", latex: "(2m+1)^2 - 2(m^2 + m) = 13 \\implies 4m^2 + 4m + 1 - 2m^2 - 2m = 13 \\implies 2m^2 + 2m - 12 = 0" },
            { type: "text", text: "化简得 $m^2 + m - 6 = 0$，解得 $(m+3)(m-2) = 0$，即 $m = 2$ 或 $m = -3$。" },
          ],
          scoring_rubric: [
            { step: 1, score_x100: 400, criterion: "第(1)问正确展开并化简判别式 $\\Delta = 1$" },
            { step: 2, score_x100: 400, criterion: "明确指出 $\\Delta > 0$ 恒成立完成证明" },
            { step: 3, score_x100: 400, criterion: "第(2)问列出韦达定理关系式" },
            { step: 4, score_x100: 600, criterion: "建立关于 $m$ 的方程并正确求解得 $m=2$ 或 $m=-3$" },
          ],
        },
      ],
    },
  },
];
