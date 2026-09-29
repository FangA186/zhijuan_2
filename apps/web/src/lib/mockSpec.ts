import { ExamSpec } from '../types/spec';

/**
 * 预设试卷规格 1: 初中九年级数学 (一元二次方程与相似三角形)
 */
export const mockJuniorMathSpec: ExamSpec = {
  title: "2026年秋季学期九年级数学月度诊断评估卷",
  curriculum_system: "教育部义务教育课程标准",
  region: "通用标准",
  stage: "junior",
  stage_year: 9,
  grade_label: "九年级",
  subject_code: "MATH_JUNIOR",
  subject_label: "初中数学",
  textbook: "人教版九年级上册",
  module: "一元二次方程与几何图形相似",
  taught_scope: {
    topics: ["一元二次方程根的判别式", "韦达定理根与系数的关系", "相似三角形判定定理", "相似三角形面积比"],
    excluded_topics: ["二次函数综合大题", "圆的切线证明", "三元一次方程组"],
    permitted_methods: ["因式分解法", "求根公式法", "比例线段推导"],
    scope_confirmed: true,
  },
  purpose: "diagnosis",
  usage_context: "school_daily_exam",
  delivery_mode: "paper",
  total_score_x100: 10000, // 100分
  duration_minutes: 90,
  sections: [
    {
      id: "sec_1",
      title: "一、单项选择题 (本大题共4小题，每小题4分，共16分)",
      question_type: "single_choice",
      count: 4,
      score_each_x100: 400,
      topics: ["一元二次方程判别式", "相似三角形判定", "根与系数关系"],
    },
    {
      id: "sec_2",
      title: "二、填空题 (本大题共3小题，每小题4分，共12分)",
      question_type: "fill_blank",
      count: 3,
      score_each_x100: 400,
      topics: ["比例中项", "韦达定理", "方程的实数根"],
    },
    {
      id: "sec_3",
      title: "三、解答与证明题 (本大题共4小题，共72分)",
      question_type: "solution",
      count: 4,
      score_each_x100: 1800,
      topics: ["方程综合求解", "相似三角形证明与面积计算"],
    },
  ],
  difficulty_distribution: {
    basic: 60,
    medium: 30,
    advanced: 10,
  },
  output_preferences: {
    paper_size: "A4",
    font_size_pt: 11,
    include_answer_space: true,
  },
};
