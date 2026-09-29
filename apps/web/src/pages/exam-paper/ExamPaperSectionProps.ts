import { GeneratedCandidate } from '../../types/candidate';

export interface ExamPaperSectionProps {
  multipleChoicePartialScoreX100?: number;
  singleChoiceQuestions: GeneratedCandidate[];
  multipleChoiceQuestions: GeneratedCandidate[];
  fillBlankQuestions: GeneratedCandidate[];
  solutionQuestions: GeneratedCandidate[];
  singleChoiceTotal: number;
  multipleChoiceTotal: number;
  fillBlankTotal: number;
  solutionTotal: number;
  viewMode: 'student' | 'teacher';
  checkLabel: (localId: string) => string;
  getSafeAnswerText: (answer: any, question?: GeneratedCandidate['public']) => string;
}
