import { ExamSection } from '../types/spec';

export interface ReferenceTemplate {
  id: string;
  name: string;
  badge: string;
  duration_minutes: number;
  total_score: number;
  description: string;
  sections: ExamSection[];
}

export const REFERENCE_TEMPLATES: ReferenceTemplate[] = [
  {
    id: 'standard_100',
    name: '标准期末综合统考卷模板',
    badge: '官方标准',
    duration_minutes: 90,
    total_score: 100,
    description: '适用于学期期末、期中标准化大型测试，结构严谨，难易度梯度分明。',
    sections: [
      {
        id: 'sec_1',
        title: '一、单项选择题 (本大题共4小题，每小题4分，共16分)',
        question_type: 'single_choice',
        count: 4,
        score_each_x100: 400,
        topics: [],
      },
      {
        id: 'sec_2',
        title: '二、填空题 (本大题共3小题，每小题4分，共12分)',
        question_type: 'fill_blank',
        count: 3,
        score_each_x100: 400,
        topics: [],
      },
      {
        id: 'sec_3',
        title: '三、解答与综合探究题 (本大题共4小题，共72分)',
        question_type: 'solution',
        count: 4,
        score_each_x100: 1800,
        topics: [],
      },
    ],
  },
  {
    id: 'elite_120',
    name: '名校联考月度诊断卷模板',
    badge: '培优提分',
    duration_minutes: 120,
    total_score: 120,
    description: '适用于重点班月考、阶段联考拔高诊断，题目数量充实，兼顾思维深度。',
    sections: [
      {
        id: 'sec_1',
        title: '一、单项选择题 (本大题共6小题，每小题4分，共24分)',
        question_type: 'single_choice',
        count: 6,
        score_each_x100: 400,
        topics: [],
      },
      {
        id: 'sec_2',
        title: '二、填空题 (本大题共4小题，每小题4分，共16分)',
        question_type: 'fill_blank',
        count: 4,
        score_each_x100: 400,
        topics: [],
      },
      {
        id: 'sec_3',
        title: '三、解答与综合大题 (本大题共5小题，共80分)',
        question_type: 'solution',
        count: 5,
        score_each_x100: 1600,
        topics: [],
      },
    ],
  },
  {
    id: 'quiz_50',
    name: '随堂分层达标小测模板',
    badge: '快速巩固',
    duration_minutes: 25,
    total_score: 50,
    description: '适用于课前小测、当堂过关检测或课后作业抽检，25分钟精准反馈。',
    sections: [
      {
        id: 'sec_1',
        title: '一、基础选择题 (共3题，每题6分，共18分)',
        question_type: 'single_choice',
        count: 3,
        score_each_x100: 600,
        topics: [],
      },
      {
        id: 'sec_2',
        title: '二、针对填空题 (共2题，每题6分，共12分)',
        question_type: 'fill_blank',
        count: 2,
        score_each_x100: 600,
        topics: [],
      },
      {
        id: 'sec_3',
        title: '三、典型解答题 (共1题，共20分)',
        question_type: 'solution',
        count: 1,
        score_each_x100: 2000,
        topics: [],
      },
    ],
  },
];
