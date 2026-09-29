import { ExamSpec } from '../../types/spec';

export interface PendingScopeSwitch {
  nextSpec: ExamSpec;
  staleTextbook: string[];
  staleTemplate: string[];
  manual: string[];
}

