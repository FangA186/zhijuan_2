import { ApiCurriculum } from './apiCurriculum';
import { ParsedTemplateResult } from './apiTypes';

export class ApiExamFiles extends ApiCurriculum {
  /**
   * 发布试卷 (调用后端发布门禁与双快照指纹计算)
   */
  public async publishExam(examId: string = 'current', payload?: any): Promise<any> {
    try {
      const res = await fetch(`${this.baseUrl}/exams/${examId}/publish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload || {}),
      });
      if (res.ok) {
        const pub = await res.json();
        const spec = await this.getExamSpec();
        const candidates = await this.getCandidates();
        const existing = await this.getExamList();
        const newRecord = {
          id: pub.snapshot_id,
          exam_id: examId,
          title: spec.title,
          stage_label: `${spec.grade_label} · ${spec.subject_label}`,
          status: 'PUBLISHED',
          total_score_x100: spec.total_score_x100,
          question_count: candidates.length,
          revision: pub.revision,
          content_hash: pub.content_hash,
          render_hash: pub.render_hash,
          created_at: pub.published_at || new Date().toLocaleString(),
          isCurrent: true,
        };
        const updated = [newRecord, ...existing.filter((e: any) => e.id !== pub.snapshot_id)];
        localStorage.setItem('zhijuan_history_exams', JSON.stringify(updated));
        return pub;
      }
      const err = await res.json().catch(() => ({ detail: '发布门禁检查失败' }));
      throw new Error(err.detail || '发布门禁检查失败');
    } catch (e: any) {
      if (this.isMockMode) {
        // Fallback for mock mode
        const spec = await this.getExamSpec();
        const candidates = await this.getCandidates();
        const mockPub = {
          snapshot_id: `snap_pub_${Date.now()}`,
          exam_id: examId,
          revision: 1,
          content_hash: 'sha256:4a81cf208a0029bc41d2f...b983a0194e1e',
          render_hash: 'render_sha256:9c12e8401aa89f1...29c491aa2810',
          status: 'PUBLISHED',
          published_at: new Date().toLocaleString(),
        };
        const existing = await this.getExamList();
        const newRecord = {
          id: mockPub.snapshot_id,
          title: spec.title,
          stage_label: `${spec.grade_label} · ${spec.subject_label}`,
          status: 'PUBLISHED',
          total_score_x100: spec.total_score_x100,
          question_count: candidates.length,
          revision: 1,
          content_hash: mockPub.content_hash,
          render_hash: mockPub.render_hash,
          created_at: mockPub.published_at,
          isCurrent: true,
        };
        const updated = [newRecord, ...existing.filter((e: any) => e.id !== mockPub.snapshot_id)];
        localStorage.setItem('zhijuan_history_exams', JSON.stringify(updated));
        return mockPub;
      }
      throw e;
    }
  }

  /**
   * 获取组织已发布或历史试卷清单
   */
  public async getExamList(): Promise<any[]> {
    if (!this.isMockMode) {
      const res = await fetch(`${this.baseUrl}/exams`);
      const data = await this.responseJson<{ items: any[] }>(res);
      return data.items;
    }
    try {
      const res = await fetch(`${this.baseUrl}/exams`);
      if (res.ok) {
        const data = await res.json();
        if (data.items && data.items.length > 0) {
          return data.items;
        }
      }
    } catch (e) {
      // Ignore network error and use local fallback
    }

    const stored = localStorage.getItem('zhijuan_history_exams');
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {}
    }
    return [];
  }

  /**
   * 上传试卷模板文件并由后端提取大题结构（需教师核对）。
   */
  public async parseExamTemplate(file: File): Promise<ParsedTemplateResult> {
    const base64Content = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        resolve(result);
      };
      reader.onerror = (err) => reject(err);
      reader.readAsDataURL(file);
    });

    const res = await fetch(`${this.baseUrl}/exams/templates/parse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: file.name,
        content_base64: base64Content,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '模板解析失败' }));
      throw new Error(err.detail || `模板解析服务返回错误 (${res.status})`);
    }

    return res.json();
  }

  
}
