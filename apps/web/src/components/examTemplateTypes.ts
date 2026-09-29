import { ExamSection } from '../types/spec';

export interface ParsedExamTemplate {
  fileName: string;
  title: string;
  total_score: number;
  duration_minutes: number;
  sections: ExamSection[];
  warnings: string[];
}
