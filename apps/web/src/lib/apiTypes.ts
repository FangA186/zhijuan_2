import { ExamSection } from '../types/spec';

export interface ParsedTemplateResult {
  title: string;
  duration_minutes: number;
  total_score: number;
  total_score_x100: number;
  sections: ExamSection[];
  engine_used?: string;
  warnings?: string[];
}
