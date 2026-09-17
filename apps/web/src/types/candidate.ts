import { QuestionKind } from './spec';

export type Block =
  | { type: 'text'; text: string }
  | { type: 'math'; latex: string }
  | { type: 'asset'; asset_id: string; alt: string }
  | { type: 'table'; headers: string[]; rows: string[][] };

export interface Option {
  id: string; // e.g. 'opt_A', 'opt_B'
  label?: string; // e.g. 'A', 'B'
  content: Block[];
}

export interface QuestionPublic {
  local_id: string;
  kind: QuestionKind;
  prompt: Block[];
  options: Option[];
  score_x100: number;
  material_ids: string[];
  children: QuestionPublic[];
  answer_space_lines: number;
}

export interface ScoreUnit {
  step: number;
  score_x100: number;
  criterion: string;
  key_expression?: string;
}

export interface AnswerItem {
  target_local_id: string;
  answer_text: string;
  selected_option_ids?: string[];
  explanation: Block[];
  scoring_rubric: ScoreUnit[];
}

export interface QuestionPrivate {
  answers: AnswerItem[];
}

export interface GeneratedCandidate {
  public: QuestionPublic;
  private: QuestionPrivate;
}
