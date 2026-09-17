import { GeneratedCandidate, QuestionPublic } from '../types/candidate';

/**
 * 公开投影 (Public Projection):
 * 彻底过滤候选题目中的私有答案 (private answers)、评分细则 (scoring_rubric) 及解析 (explanation)。
 * 返回纯净的学生卷题面数据结构。
 */
export function makePublicProjection(candidate: GeneratedCandidate): QuestionPublic {
  // 深拷贝 public 题面，确保不携带任何 private 引用
  const pub = JSON.parse(JSON.stringify(candidate.public)) as QuestionPublic;

  // 递归处理子题
  if (pub.children && pub.children.length > 0) {
    pub.children = pub.children.map((child) => {
      // 保证子题同样符合 QuestionPublic 结构
      return {
        local_id: child.local_id,
        kind: child.kind,
        prompt: child.prompt,
        options: child.options,
        score_x100: child.score_x100,
        material_ids: child.material_ids,
        children: child.children ? makePublicProjection({ public: child, private: { answers: [] } }).children : [],
        answer_space_lines: child.answer_space_lines,
      };
    });
  }

  return pub;
}

/**
 * 批量生成整卷学生版公开投影
 */
export function makeExamPublicProjection(candidates: GeneratedCandidate[]): QuestionPublic[] {
  return candidates.map(makePublicProjection);
}
