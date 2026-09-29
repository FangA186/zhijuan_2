import { ExamBlueprint } from '../types/spec';
import type { PlanningJob } from '../types/planning';
import { STORAGE_KEYS, ApiBase } from './apiBase';
import { mockMathSlots } from './mockData';

export class ApiBlueprint extends ApiBase {
  /**
   * 获取或生成蓝图 Blueprint
   */
  public async getBlueprint(): Promise<ExamBlueprint> {
    if (this.isMockMode) {
      const stored = localStorage.getItem(STORAGE_KEYS.BLUEPRINT);
      if (stored) {
        try { return JSON.parse(stored); } catch { /* fallback */ }
      }
      const initial: ExamBlueprint = {
        exam_id: 'exam_demo_01',
        plan_id: 'plan_rev_1',
        revision: 1,
        confirmed: true,
        slots: mockMathSlots,
        total_score_x100: 10000,
        created_at: new Date().toISOString(),
      };
      localStorage.setItem(STORAGE_KEYS.BLUEPRINT, JSON.stringify(initial));
      return initial;
    }
    const res = await fetch(`${this.baseUrl}/exams/current/plans/current`);
    return this.responseJson<ExamBlueprint>(res);
  }

  public async startPlanning(requestKey: string): Promise<PlanningJob> {
    if (this.isMockMode) throw new Error('规划 Agent 需要真实服务，不能以模拟计划代替');
    const res = await fetch(`${this.baseUrl}/exams/current/planning-jobs`, {
      method: 'POST', headers: { 'Idempotency-Key': requestKey, ...(this.specEtag ? { 'If-Match': this.specEtag } : {}) },
    });
    return this.responseJson<PlanningJob>(res);
  }

  public async getPlanning(): Promise<PlanningJob | null> {
    const res = await fetch(`${this.baseUrl}/exams/current/planning-jobs/current`);
    return this.responseJson<PlanningJob | null>(res);
  }

  public async cancelPlanning(jobId: string): Promise<PlanningJob> {
    const res = await fetch(`${this.baseUrl}/exams/current/planning-jobs/${jobId}/cancel`, { method: 'POST' });
    return this.responseJson<PlanningJob>(res);
  }

  /**
   * 确认蓝图
   */
  public async confirmBlueprint(blueprint: ExamBlueprint): Promise<ExamBlueprint> {
    if (this.isMockMode) {
      const updated = { ...blueprint, confirmed: true, revision: blueprint.revision + 1 };
      localStorage.setItem(STORAGE_KEYS.BLUEPRINT, JSON.stringify(updated));
      return updated;
    }
    const res = await fetch(`${this.baseUrl}/exams/current/plans/${blueprint.plan_id}/confirm`, {
      method: 'POST',
      headers: this.specEtag ? { 'If-Match': this.specEtag } : {},
    });
    return this.responseJson<ExamBlueprint>(res);
  }

  
}
