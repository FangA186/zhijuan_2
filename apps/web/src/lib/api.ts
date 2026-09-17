import { ExamSpec, ExamBlueprint, ChapterTreeNode, TextbookSummary } from '../types/spec';
import { GeneratedCandidate } from '../types/candidate';
import { ValidationRecord, AdjudicationRecord } from '../types/validation';
import { GenerationJob } from '../types/job';
import { mockJuniorMathSpec, mockMathSlots, mockMathCandidates, mockValidationRecords } from './mockData';

const STORAGE_KEYS = {
  SPEC: 'zhijuan_exam_spec',
  BLUEPRINT: 'zhijuan_exam_blueprint',
  CANDIDATES: 'zhijuan_exam_candidates',
  VALIDATION: 'zhijuan_exam_validation',
  ADJUDICATIONS: 'zhijuan_exam_adjudications',
  MODE: 'zhijuan_api_mode',
};

class ZhijuanApiClient {
  private isMockMode: boolean = true;
  private baseUrl: string = 'http://localhost:8000/v1';

  constructor() {
    const savedMode = localStorage.getItem(STORAGE_KEYS.MODE);
    this.isMockMode = savedMode ? savedMode === 'mock' : true;
  }

  public getMode(): 'mock' | 'live' {
    return this.isMockMode ? 'mock' : 'live';
  }

  public setMode(mode: 'mock' | 'live') {
    this.isMockMode = mode === 'mock';
    localStorage.setItem(STORAGE_KEYS.MODE, mode);
  }

  /**
   * 初始化/获取当前试卷规格 ExamSpec
   */
  public async getExamSpec(): Promise<ExamSpec> {
    if (this.isMockMode) {
      const stored = localStorage.getItem(STORAGE_KEYS.SPEC);
      if (stored) {
        try { return JSON.parse(stored); } catch { /* fallback */ }
      }
      localStorage.setItem(STORAGE_KEYS.SPEC, JSON.stringify(mockJuniorMathSpec));
      return mockJuniorMathSpec;
    }
    const res = await fetch(`${this.baseUrl}/exams/current/spec`);
    return res.json();
  }

  /**
   * 保存试卷规格
   */
  public async saveExamSpec(spec: ExamSpec): Promise<ExamSpec> {
    if (this.isMockMode) {
      localStorage.setItem(STORAGE_KEYS.SPEC, JSON.stringify(spec));
      return spec;
    }
    const res = await fetch(`${this.baseUrl}/exams/current/spec`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(spec),
    });
    return res.json();
  }

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
    return res.json();
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
    });
    return res.json();
  }

  /**
   * 启动生成任务
   */
  public async startGenerationJob(examId: string): Promise<GenerationJob> {
    if (this.isMockMode) {
      const bp = await this.getBlueprint();
      return {
        job_id: `job_${Date.now()}`,
        exam_id: examId,
        revision: bp.revision,
        status: 'RUNNING',
        total_slots: bp.slots.length,
        completed_slots: 0,
        tokens_used: 12500,
        estimated_cost_cny: 0.18,
        started_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        slots: bp.slots.map(s => ({ ...s, status: 'PENDING' })),
        logs: [
          { timestamp: new Date().toISOString(), role: 'planner', level: 'info', message: '蓝图确认完毕，分配槽位任务...' },
          { timestamp: new Date().toISOString(), role: 'system', level: 'info', message: 'Celery Worker 启动，初始化沙箱目录与只读 Skills...' },
        ],
      };
    }
    const res = await fetch(`${this.baseUrl}/exams/${examId}/generation-jobs`, { method: 'POST' });
    return res.json();
  }

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
    return res.json();
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
    return res.json();
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
    return res.json();
  }

  /**
   * 获取人工裁决记录
   */
  public async getAdjudications(): Promise<Record<string, AdjudicationRecord>> {
    const stored = localStorage.getItem(STORAGE_KEYS.ADJUDICATIONS);
    return stored ? JSON.parse(stored) : {};
  }

  /**
   * 提交人工裁决
   */
  public async submitAdjudication(record: AdjudicationRecord): Promise<void> {
    const adjudications = await this.getAdjudications();
    adjudications[record.item_id] = record;
    localStorage.setItem(STORAGE_KEYS.ADJUDICATIONS, JSON.stringify(adjudications));
  }

  /**
   * 获取 SmartEdu 官方分类层级标签树
   */
  public async getCurriculumTags(): Promise<any> {
    try {
      const res = await fetch(`${this.baseUrl}/curriculum/tags`);
      if (!res.ok) throw new Error('Failed to fetch tags');
      return await res.json();
    } catch (e) {
      console.warn('Failed to load tags from API', e);
      return null;
    }
  }

  /**
   * 搜索与级联获取教材清单
   */
  public async getCurriculumMaterials(params?: {
    mode?: 'visible' | 'all';
    stage?: string;
    grade?: string;
    subject?: string;
    edition?: string;
    term?: string;
    q?: string;
    limit?: number;
  }): Promise<{ total: number; mode: string; count: number; items: TextbookSummary[] }> {
    const searchParams = new URLSearchParams();
    if (params?.mode) searchParams.set('mode', params.mode);
    if (params?.stage) searchParams.set('stage', params.stage);
    if (params?.grade) searchParams.set('grade', params.grade);
    if (params?.subject) searchParams.set('subject', params.subject);
    if (params?.edition) searchParams.set('edition', params.edition);
    if (params?.term) searchParams.set('term', params.term);
    if (params?.q) searchParams.set('q', params.q);
    if (params?.limit) searchParams.set('limit', String(params.limit));

    try {
      const res = await fetch(`${this.baseUrl}/curriculum/materials?${searchParams.toString()}`);
      if (!res.ok) throw new Error('Failed to fetch materials');
      return await res.json();
    } catch (e) {
      console.error('Failed to load materials from API', e);
      return { total: 0, mode: params?.mode || 'visible', count: 0, items: [] };
    }
  }

  /**
   * 获取单本教材详情
   */
  public async getCurriculumMaterial(materialId: string): Promise<{ summary: TextbookSummary; details: any } | null> {
    try {
      const res = await fetch(`${this.baseUrl}/curriculum/materials/${materialId}`);
      if (!res.ok) throw new Error('Failed to fetch material');
      return await res.json();
    } catch (e) {
      console.error('Failed to load material', e);
      return null;
    }
  }

  /**
   * 获取单本教材的完整章节目录树
   */
  public async getMaterialChapterTree(materialId: string): Promise<{ material_id: string; chapters: ChapterTreeNode[] } | null> {
    try {
      const res = await fetch(`${this.baseUrl}/curriculum/materials/${materialId}/tree`);
      if (!res.ok) throw new Error('Failed to fetch chapter tree');
      return await res.json();
    } catch (e) {
      console.error('Failed to load chapter tree', e);
      return null;
    }
  }

  /**
   * 重置 Mock 存储回初始状态
   */
  public resetMockData() {
    localStorage.removeItem(STORAGE_KEYS.SPEC);
    localStorage.removeItem(STORAGE_KEYS.BLUEPRINT);
    localStorage.removeItem(STORAGE_KEYS.CANDIDATES);
    localStorage.removeItem(STORAGE_KEYS.VALIDATION);
    localStorage.removeItem(STORAGE_KEYS.ADJUDICATIONS);
  }
}

export const api = new ZhijuanApiClient();
