export type Stage = 'primary' | 'junior' | 'senior';

export type QuestionKind = 
  | 'single_choice'
  | 'multiple_choice'
  | 'true_false'
  | 'fill_blank'
  | 'solution'
  | 'short_answer'
  | 'essay'
  | 'material_group';

export interface ExamSection {
  id: string;
  title: string;
  question_type: QuestionKind;
  count: number;
  score_each_x100: number;
  total_score_x100?: number;
  item_scores_x100?: number[];
  topics: string[];
}

export interface TaughtScope {
  topics: string[];
  excluded_topics: string[];
  permitted_methods: string[];
  scope_confirmed: boolean;
}

export interface DifficultyDistribution {
  basic: number;
  medium: number;
  advanced: number;
}

export interface OutputPreferences {
  paper_size: 'A4' | 'A3';
  font_size_pt: number;
  include_answer_space: boolean;
}

export interface ProvidedMaterial {
  id: string;
  title: string;
  text: string;
  source_note: string;
  rights_confirmed: boolean;
}

export interface ChineseSpecConfig {
  poetry_list: string[];           // 指定考查的古诗文篇目
  theme_prompt?: string;           // 选文立意与命题主题提示词
  writing_prompt?: string;         // 作文立意与文体要求
}

export interface EnglishSpecConfig {
  vocab_level?: 'primary_800' | 'junior_1600' | 'senior_3500'; // 词汇量基线（预留，前端已不再维护）
  focus_words?: string[];          // 本次重点考查单词/词组（预留，前端已不再维护）
  passage_themes?: string[];       // 语篇题材偏好
  theme_prompt?: string;           // 额外命题与写作提示词
  active_vocab_images?: TextbookVocabImage[]; // 用户自定义/过滤后的词表图片列表
  is_vocab_customized?: boolean;   // 是否已被用户手动自定义更改
}

export interface ExamSpec {
  multiple_choice_partial_score_x100?: number;
  title: string;
  curriculum_system: string;
  region: string;
  stage: Stage;
  stage_year: number;
  grade_label: string;
  subject_code: string;
  subject_label: string;
  textbook: string | null;
  module: string | null;
  material_id?: string;
  textbook_cover?: string;
  taught_scope: TaughtScope;
  purpose: 'practice' | 'diagnosis' | 'review' | 'formal';
  usage_context: 'personal_learning' | 'school_daily_exam' | 'other';
  delivery_mode: 'paper' | 'digital';
  total_score_x100: number;
  duration_minutes: number | null;
  sections: ExamSection[];
  difficulty_distribution: DifficultyDistribution;
  output_preferences: OutputPreferences;
  provided_materials?: ProvidedMaterial[];
  chinese_config?: ChineseSpecConfig;
  english_config?: EnglishSpecConfig;
}

export interface ChapterTreeNode {
  id: string;
  title: string;
  description?: string | null;
  chapter_type?: string | null;
  child_nodes?: ChapterTreeNode[] | null;
}

export interface TextbookSummary {
  id: string;
  title: string;
  thumb?: string;
  tag_ids?: string[];
  dims?: Record<string, { id: string; name: string }>;
  isVisible?: boolean;
  visReason?: string;
  visCode?: string;
  hasVocab?: boolean;
  vocabCount?: number;
}

export interface TextbookVocabImage {
  filename: string;
  page_num: number;
  order: number;
  rel_path: string;
  url: string;
}

export interface TextbookVocabData {
  material_id: string;
  title: string;
  stage: string;
  edition: string;
  grade: string;
  term: string;
  folder_path: string;
  image_count: number;
  start_page: number | null;
  end_page: number | null;
  page_range: number[];
  images: TextbookVocabImage[];
  summary: string;
}

export interface BlueprintSlot {
  slot_id: string;
  order: number;
  section_id: string;
  kind: QuestionKind;
  target_topic: string;
  cognitive_target: string;
  design_brief?: string;
  planning_rationale?: string;
  knowledge_ids?: string[];
  estimated_difficulty: 'basic' | 'medium' | 'advanced';
  score_x100: number;
  answer_space_lines: number;
  material_id?: string;
  status: 'PENDING' | 'AUTHORING' | 'SOLVING' | 'CHECKING' | 'REPAIRING' | 'READY' | 'REVIEW_REQUIRED' | 'FAIL';
}

export interface ExamBlueprint {
  planning_source?: string;
  planning_summary?: string;
  exam_id: string;
  plan_id: string;
  revision: number;
  spec_revision?: number;
  plan_revision?: number;
  plan_hash?: string;
  confirmed: boolean;
  slots: BlueprintSlot[];
  total_score_x100: number;
  created_at: string;
}
