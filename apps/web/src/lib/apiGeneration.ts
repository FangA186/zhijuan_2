import { GenerationJob } from '../types/job';
import { GeneratedCandidate } from '../types/candidate';
import { ApiBlueprint } from './apiBlueprint';

export class ApiGeneration extends ApiBlueprint {
  /**
   * 启动生成任务
   */
  public async startGenerationJob(examId: string = 'current'): Promise<GenerationJob> {
    const res = await fetch(`${this.baseUrl}/exams/${examId}/generation-jobs`, {
      method: 'POST', headers: this.specEtag ? { 'If-Match': this.specEtag } : {},
    });
    return this.responseJson<GenerationJob>(res);
  }

  /**
   * 获取当前生成流水线作业状态
   */
  public async getCurrentJob(examId: string = 'current'): Promise<GenerationJob | null> {
    const res = await fetch(`${this.baseUrl}/exams/${examId}/generation-jobs/current`);
    if (res.status === 404) return null;
    return this.responseJson<GenerationJob>(res);
  }

  public async getJobActivity(): Promise<GenerationJob | null> {
    const res = await fetch(`${this.baseUrl}/exams/current/generation-jobs/activity`);
    if (res.status === 404) return null;
    return this.responseJson<GenerationJob>(res);
  }

  public getJobActivityStreamUrl(): string {
    return `${this.baseUrl}/exams/current/generation-jobs/activity/stream`;
  }

  /**
   * 单步/推进当前生成作业
   */
  public async stepGenerationJob(examId: string = 'current', slotId?: string): Promise<GenerationJob | null> {
    const url = slotId
        ? `${this.baseUrl}/exams/${examId}/generation-jobs/current/step?slot_id=${slotId}`
        : `${this.baseUrl}/exams/${examId}/generation-jobs/current/step`;
    const res = await fetch(url, { method: 'POST' });
    return this.responseJson<GenerationJob>(res);
  }

  /**
   * 获取流水线实时 Server-Sent Events (SSE) 协议 URL
   */
  public getGenerationJobStreamUrl(examId: string = 'current'): string {
    return `${this.baseUrl}/exams/${examId}/generation-jobs/stream`;
  }

  /**
   * 暂停生成流水线
   */
  public async pauseGenerationJob(examId: string = 'current'): Promise<GenerationJob | null> {
    const res = await fetch(`${this.baseUrl}/exams/${examId}/generation-jobs/current/pause`, { method: 'POST' });
    return this.responseJson<GenerationJob>(res);
  }

  /**
   * 恢复生成流水线
   */
  public async resumeGenerationJob(examId: string = 'current'): Promise<GenerationJob | null> {
    const res = await fetch(`${this.baseUrl}/exams/${examId}/generation-jobs/current/resume`, { method: 'POST' });
    return this.responseJson<GenerationJob>(res);
  }

  /**
   * 取消生成流水线
   */
  public async cancelGenerationJob(examId: string = 'current'): Promise<GenerationJob | null> {
    const res = await fetch(`${this.baseUrl}/exams/${examId}/generation-jobs/current/cancel`, { method: 'POST' });
    return this.responseJson<GenerationJob>(res);
  }

  /**
   * 单题槽重新生成
   */
  public async regenerateSlot(slotId: string, examId: string = 'current'): Promise<GeneratedCandidate | null> {
    const res = await fetch(`${this.baseUrl}/exams/${examId}/slots/${slotId}/regenerate`, { method: 'POST' });
    return this.responseJson<GeneratedCandidate>(res);
  }

  
}
