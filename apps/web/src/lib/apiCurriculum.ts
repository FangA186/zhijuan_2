import { ChapterTreeNode, TextbookSummary, TextbookVocabData, TextbookVocabImage } from '../types/spec';
import { ApiCandidates } from './apiCandidates';

export class ApiCurriculum extends ApiCandidates {
  /**
   * 获取 SmartEdu 官方分类层级标签树
   */
  public async getCurriculumTags(): Promise<any> {
    const res = await fetch(`${this.baseUrl}/curriculum/tags`);
    return this.responseJson(res);
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

    const res = await fetch(`${this.baseUrl}/curriculum/materials?${searchParams.toString()}`);
    return this.responseJson(res);
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
   * 获取教材对应的原版高清词汇表及图片列表
   */
  public async getMaterialVocab(materialId: string): Promise<TextbookVocabData | null> {
    try {
      const res = await fetch(`${this.baseUrl}/curriculum/materials/${materialId}/vocab`);
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      console.warn('Failed to load textbook vocab data', e);
      return null;
    }
  }

  /**
   * 上传自定义词表图片 (Base64 JSON)
   */
  public async uploadVocabImage(file: File): Promise<TextbookVocabImage> {
    const base64Content = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = (err) => reject(err);
      reader.readAsDataURL(file);
    });

    const res = await fetch(`${this.baseUrl}/curriculum/vocab/upload`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: file.name,
        content_base64: base64Content,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }

    const data = await res.json();
    return {
      filename: data.filename,
      page_num: data.page_num || 1,
      order: data.order || 1,
      rel_path: data.rel_path || `custom/${data.filename}`,
      url: data.url,
    };
  }

  /**
   * 获取词汇表高清图片的完整 URL (支持官方原版与用户自定义上传)
   */
  public getVocabImageUrl(materialId: string, filename: string, customUrl?: string): string {
    if (customUrl) {
      if (customUrl.startsWith('http')) return customUrl;
      return `${this.baseUrl.replace(/\/v1$/, '')}${customUrl}`;
    }
    if (filename.startsWith('custom_')) {
      return `${this.baseUrl}/curriculum/vocab/custom-images/${encodeURIComponent(filename)}`;
    }
    return `${this.baseUrl}/curriculum/materials/${materialId}/vocab/images/${encodeURIComponent(filename)}`;
  }

  
}
