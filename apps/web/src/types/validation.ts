export type CheckStatus = 'PASS' | 'REVIEW' | 'FAIL';

export interface RuleCheckResult {
  rule_id: string;
  category: 'structure' | 'math_consistency' | 'scope_adherence' | 'anti_leakage';
  name: string;
  status: CheckStatus;
  detail: string;
  evidence?: string;
}

export interface BlindSolveStep {
  step_number: number;
  description: string;
  expression?: string;
}

export interface BlindSolveReport {
  solver_role: string;
  model_id: string;
  is_same_model: boolean;
  derived_answer: string;
  selected_option_ids?: string[];
  steps: BlindSolveStep[];
  match_reference: boolean;
  notes: string;
  duration_ms: number;
}

export interface ValidationRecord {
  local_id: string;
  overall_status: CheckStatus;
  rule_checks: RuleCheckResult[];
  blind_solve: BlindSolveReport;
  verified_at: string;
  content_hash: string;
  repair_count: number;
}

export interface AdjudicationRecord {
  item_id: string;
  decision: 'ACCEPT' | 'REJECT';
  reviewer_name: string;
  reviewer_role: string;
  reason: string;
  timestamp: string;
}
