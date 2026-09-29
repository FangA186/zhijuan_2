import type { ExamSpec, ExamSection } from '../../types/spec';

export interface PresetDefinition {
  id: 'quiz' | 'monthly' | 'final';
  title: string;
  badge: string;
  isBest?: boolean;
  purpose: ExamSpec['purpose'];
  duration_minutes: number;
  total_score_x100: number;
  buildSections: (topics: string[]) => ExamSection[];
}

export const PRESET_DEFINITIONS: PresetDefinition[] = [
  {
    id: 'quiz',
    title: '随堂小测',
    badge: '高效检测',
    purpose: 'practice',
    duration_minutes: 25,
    total_score_x100: 5000,
    buildSections: (topics) => [
      { id: 'sec_1', title: '一、选择题 (共3题，每题6分，共18分)', question_type: 'single_choice', count: 3, score_each_x100: 600, topics: topics.slice(0, 2) },
      { id: 'sec_2', title: '二、填空题 (共2题，每题6分，共12分)', question_type: 'fill_blank', count: 2, score_each_x100: 600, topics: topics.slice(1, 3) },
      { id: 'sec_3', title: '三、解答题 (共1题，共20分)', question_type: 'solution', count: 1, score_each_x100: 2000, topics: topics.slice(0, 2) },
    ],
  },
  {
    id: 'monthly',
    title: '单元月考',
    badge: '常用推荐',
    isBest: true,
    purpose: 'diagnosis',
    duration_minutes: 90,
    total_score_x100: 10000,
    buildSections: (topics) => [
      { id: 'sec_1', title: '一、单项选择题 (本大题共4小题，每小题4分，共16分)', question_type: 'single_choice', count: 4, score_each_x100: 400, topics },
      { id: 'sec_2', title: '二、填空题 (本大题共3小题，每小题4分，共12分)', question_type: 'fill_blank', count: 3, score_each_x100: 400, topics },
      { id: 'sec_3', title: '三、解答与证明题 (本大题共4小题，共72分)', question_type: 'solution', count: 4, score_each_x100: 1800, topics },
    ],
  },
  {
    id: 'final',
    title: '期中期末模拟',
    badge: '综合全卷',
    purpose: 'formal',
    duration_minutes: 120,
    total_score_x100: 12000,
    buildSections: (topics) => [
      { id: 'sec_1', title: '一、单项选择题 (本大题共6小题，每小题4分，共24分)', question_type: 'single_choice', count: 6, score_each_x100: 400, topics },
      { id: 'sec_2', title: '二、填空题 (本大题共4小题，每小题4分，共16分)', question_type: 'fill_blank', count: 4, score_each_x100: 400, topics },
      { id: 'sec_3', title: '三、解答与综合大题 (本大题共5小题，共80分)', question_type: 'solution', count: 5, score_each_x100: 1600, topics },
    ],
  },
];

