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

export interface ExamSpec {
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
}

export interface BlueprintSlot {
  slot_id: string;
  order: number;
  section_id: string;
  kind: QuestionKind;
  target_topic: string;
  cognitive_target: string;
  estimated_difficulty: 'basic' | 'medium' | 'advanced';
  score_x100: number;
  answer_space_lines: number;
  material_id?: string;
  status: 'PENDING' | 'AUTHORING' | 'SOLVING' | 'CHECKING' | 'REPAIRING' | 'READY' | 'REVIEW_REQUIRED' | 'FAIL';
}

export interface ExamBlueprint {
  exam_id: string;
  plan_id: string;
  revision: number;
  confirmed: boolean;
  slots: BlueprintSlot[];
  total_score_x100: number;
  created_at: string;
}
