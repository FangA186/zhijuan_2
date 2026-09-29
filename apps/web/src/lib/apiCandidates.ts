import { GeneratedCandidate } from '../types/candidate';
import { ValidationRecord, AdjudicationRecord } from '../types/validation';
import { ApiGeneration } from './apiGeneration';
import { STORAGE_KEYS } from './apiBase';
import { mockMathCandidates, mockValidationRecords } from './mockData';

export class ApiCandidates extends ApiGeneration {
  /**
   * 获取所有题目候选数据
   */
  public async getCandidates(): Promise<GeneratedCandidate[]> {
    if (this.isMockMode) {
      const stored = localStorage.getItem(STORAGE_KEYS.CANDIDATES);
      if (stored) {
        try { return JSON.parse(stored); } catch { /* fallback */ }
      }
      localStorage.setItem(STORAGE_KEYS.CANDIDATES, JSON.stringify(mockMathCandidates));
      return mockMathCandidates;
    }
    const res = await fetch(`${this.baseUrl}/exams/current/questions`);
    return this.responseJson<GeneratedCandidate[]>(res);
  }

  /**
   * 保存/修改单道题目 (支持乐观锁 If-Match 模拟)
   */
  public async updateCandidate(candidate: GeneratedCandidate): Promise<GeneratedCandidate> {
    if (this.isMockMode) {
      const list = await this.getCandidates();
      const idx = list.findIndex(c => c.public.local_id === candidate.public.local_id);
      if (idx >= 0) {
        list[idx] = candidate;
      } else {
        list.push(candidate);
      }
      localStorage.setItem(STORAGE_KEYS.CANDIDATES, JSON.stringify(list));

      // 规则：修改题面后，旧校验依据失效并自动变为 REVIEW
      const valRecords = await this.getValidationRecords();
      if (valRecords[candidate.public.local_id]) {
        valRecords[candidate.public.local_id].overall_status = 'REVIEW';
        valRecords[candidate.public.local_id].rule_checks.push({
          rule_id: 'RULE_CONTENT_CHANGED',
          category: 'structure',
          name: '题面修改再核对',
          status: 'REVIEW',
          detail: '教师手动编辑了题干或答案，旧自动校验依据已过期，需重新审验',
        });
        localStorage.setItem(STORAGE_KEYS.VALIDATION, JSON.stringify(valRecords));
      }

      return candidate;
    }
    const res = await fetch(`${this.baseUrl}/exams/current/questions/${candidate.public.local_id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(candidate),
    });
    return this.responseJson<GeneratedCandidate>(res);
  }

  /**
   * 重新生成单道题 (沿用槽位要求)
   */
  public async regenerateQuestion(localId: string): Promise<GeneratedCandidate> {
    if (this.isMockMode) {
      await new Promise(r => setTimeout(r, 1200)); // 模拟 Agent 调用
      const list = await this.getCandidates();
      const target = list.find(c => c.public.local_id === localId);
      if (target) {
        target.public.prompt = [
          { type: 'text', text: `【新版重构】若关于 $x$ 的方程 $x^2 - 6x + m = 0$ 拥有两个互不相同的实数根，则 $m$ 的范围为：` }
        ];
        target.private.answers[0].explanation = [
          { type: 'text', text: `计算判别式 $\\Delta = (-6)^2 - 4m = 36 - 4m > 0 \\implies m < 9$。` }
        ];
        localStorage.setItem(STORAGE_KEYS.CANDIDATES, JSON.stringify(list));
        return target;
      }
    }
    const res = await fetch(`${this.baseUrl}/exams/current/questions/${localId}/regenerate`, { method: 'POST' });
    return res.json();
  }

  /**
   * 获取验证记录
   */
  public async getValidationRecords(): Promise<Record<string, ValidationRecord>> {
    if (this.isMockMode) {
      const stored = localStorage.getItem(STORAGE_KEYS.VALIDATION);
      if (stored) {
        try { return JSON.parse(stored); } catch { /* fallback */ }
      }
      localStorage.setItem(STORAGE_KEYS.VALIDATION, JSON.stringify(mockValidationRecords));
      return mockValidationRecords;
    }
    const res = await fetch(`${this.baseUrl}/exams/current/validation`);
    return this.responseJson<Record<string, ValidationRecord>>(res);
  }

  /**
   * 获取人工裁决记录
   */
  public async getAdjudications(): Promise<Record<string, AdjudicationRecord>> {
    if (!this.isMockMode) {
      const res = await fetch(`${this.baseUrl}/exams/current/adjudications`);
      return this.responseJson<Record<string, AdjudicationRecord>>(res);
    }
    const stored = localStorage.getItem(STORAGE_KEYS.ADJUDICATIONS);
    return stored ? JSON.parse(stored) : {};
  }

  /**
   * 提交人工裁决
   */
  public async submitAdjudication(record: AdjudicationRecord): Promise<void> {
    if (!this.isMockMode) {
      const res = await fetch(`${this.baseUrl}/exams/current/adjudications`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(record),
      });
      await this.responseJson(res);
      return;
    }
    const adjudications = await this.getAdjudications();
    adjudications[record.item_id] = record;
    localStorage.setItem(STORAGE_KEYS.ADJUDICATIONS, JSON.stringify(adjudications));
  }

  
}
