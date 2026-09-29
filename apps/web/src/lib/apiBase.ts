import { ExamSpec } from '../types/spec';
import { GenerationRuntimeState } from '../types/job';
import { canonicalSections } from './scoring';
import { normalizeReadiness } from './runtimeReasons';
import { mockJuniorMathSpec } from './mockData';

export const STORAGE_KEYS = {
  SPEC: 'zhijuan_exam_spec',
  BLUEPRINT: 'zhijuan_exam_blueprint',
  CANDIDATES: 'zhijuan_exam_candidates',
  VALIDATION: 'zhijuan_exam_validation',
  ADJUDICATIONS: 'zhijuan_exam_adjudications',
  MODE: 'zhijuan_api_mode',
};

export class ApiBase {
  protected isMockMode: boolean = true;
  protected baseUrl: string = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/v1';
  protected specEtag: string | null = null;

  /** 保存非 2xx 响应的元信息，供调用方区分处理 */
  public static readonly ETAG_CONFLICT = 'ETAG_CONFLICT';
  public static readonly GENERIC_ERROR = 'GENERIC_ERROR';

  protected async responseJson<T>(res: Response): Promise<T> {
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      const detail = typeof body.detail === 'string' ? body.detail
        : typeof body.reason === 'string' ? body.reason
        : `请求失败 (${res.status})`;
      // 附加状态码以便调用方区分
      const err = new Error(detail) as Error & { status?: number; code?: string; errorType?: string };
      err.status = res.status;
      err.code = body.code;
      err.errorType = res.status === 412 ? ApiBase.ETAG_CONFLICT : ApiBase.GENERIC_ERROR;
      throw err;
    }
    return res.json();
  }

  constructor() {
    this.isMockMode = false;
    localStorage.setItem(STORAGE_KEYS.MODE, 'live');
  }

  public getMode(): 'mock' | 'live' {
    return 'live';
  }

  public async getGenerationConfiguration(): Promise<{ configured: boolean }> {
    const res = await fetch(`${this.baseUrl}/health`);
    const health = await this.responseJson<{ generation: { configured: boolean } }>(res);
    return health.generation ?? { configured: false };
  }

  /**
   * C6: 对 /v1/readyz 规范化，返回前端运行状态。
   * fail-closed：服务缺字段/字段非法一律 null（未知），绝不误绿。
   * ready 仅在服务端 ready===true 且 components 全 ok 时为 true。
   * 网络失败同样返回全 null 状态，不抛异常。
   */
  public async fetchGenerationReadiness(): Promise<GenerationRuntimeState> {
    const fail: GenerationRuntimeState = {
      ready: null, configured: null, reasonCodes: [],
      components: {}, checkedAt: null, versionConfirmed: false,
    };
    try {
      const res = await fetch(`${this.baseUrl}/readyz`);
      if (!res.ok) return fail;
      const body: Record<string, unknown> = await res.json();
      return normalizeReadiness(body);
    } catch {
      return fail;
    }
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
    const spec = await this.responseJson<ExamSpec>(res);
    this.specEtag = res.headers.get('ETag');
    // Legacy demo seed used absolute school years; API writes always use years within the stage.
    if (spec.stage === 'junior' && spec.stage_year >= 7 && spec.stage_year <= 9) {
      console.warn('Migrating legacy junior stage_year from absolute school year');
      spec.stage_year -= 6;
    } else if (spec.stage === 'senior' && spec.stage_year >= 10 && spec.stage_year <= 12) {
      console.warn('Migrating legacy senior stage_year from absolute school year');
      spec.stage_year -= 9;
    }
    return spec;
  }

  /**
   * 保存试卷规格
   */
  public async saveExamSpec(spec: ExamSpec): Promise<ExamSpec> {
    if (this.isMockMode) {
      localStorage.setItem(STORAGE_KEYS.SPEC, JSON.stringify(spec));
      return spec;
    }
    const canonicalKeys: (keyof ExamSpec)[] = [
      'title', 'curriculum_system', 'region', 'stage', 'stage_year', 'grade_label',
      'subject_code', 'subject_label', 'textbook', 'module', 'taught_scope',
      'purpose', 'usage_context', 'delivery_mode', 'total_score_x100',
      'duration_minutes', 'sections', 'difficulty_distribution',
      'output_preferences', 'provided_materials', 'multiple_choice_partial_score_x100',
    ];
    const canonical = Object.fromEntries(canonicalKeys.filter(key => spec[key] !== undefined).map(key => [key, spec[key]]));
    canonical.sections = canonicalSections(spec.sections);
    const sidecar = Object.fromEntries((['material_id', 'textbook_cover', 'chinese_config', 'english_config'] as const)
      .filter(key => spec[key] !== undefined).map(key => [key, spec[key]]));
    if (!this.specEtag) await this.getExamSpec();
    if (!this.specEtag) throw new Error('服务器未返回规格版本，请刷新后重试');
    const res = await fetch(`${this.baseUrl}/exams/current/spec`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'If-Match': this.specEtag },
      body: JSON.stringify({ ...canonical, ...sidecar }),
    });
    const saved = await this.responseJson<ExamSpec>(res);
    this.specEtag = res.headers.get('ETag');
    return saved;
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
    localStorage.removeItem('zhijuan_history_exams');
  }
}
