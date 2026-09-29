import React, { useRef, useState } from 'react';
import { ExamSpec, ExamSection } from '../types/spec';
import { api, ParsedTemplateResult } from '../lib/api';
import { ExamTemplateDialog, ExamTemplateTab } from './ExamTemplateDialog';
import { ExamTemplateUploadPanel } from './ExamTemplateUploadPanel';
import { ExamTemplatePresetsPanel } from './ExamTemplatePresetsPanel';
import { ReferenceTemplate } from './examReferenceTemplates';
import { ParsedExamTemplate } from './examTemplateTypes';

interface ExamTemplateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApplyTemplate: (template: { source: 'uploaded' | 'preset'; name: string; title?: string; total_score_x100: number; duration_minutes: number; sections: ExamSection[] }) => void;
  currentSpec: ExamSpec;
}

export const ExamTemplateModal: React.FC<ExamTemplateModalProps> = ({ isOpen, onClose, onApplyTemplate, currentSpec }) => {
  const [activeTab, setActiveTab] = useState<ExamTemplateTab>('upload');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [parsedTemplate, setParsedTemplate] = useState<ParsedExamTemplate | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processFile = async (file: File) => {
    setSelectedFile(file); setIsParsing(true); setParseError(null);
    try {
      const result: ParsedTemplateResult = await api.parseExamTemplate(file);
      setParsedTemplate({ fileName: file.name, title: result.title || file.name.replace(/\.[^/.]+$/, ''), total_score: result.total_score, duration_minutes: result.duration_minutes, sections: result.sections, warnings: result.warnings || [] });
    } catch (error: any) {
      console.error('Failed to parse exam template:', error);
      setParseError(error.message || '试卷结构解析失败，请检查文件格式是否有效');
    } finally { setIsParsing(false); }
  };
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => { const file = event.target.files?.[0]; if (file) void processFile(file); };
  const handleDrop = (event: React.DragEvent) => { event.preventDefault(); const file = event.dataTransfer.files?.[0]; if (file) void processFile(file); };
  const handleApplyParsed = () => {
    if (!parsedTemplate) return;
    onApplyTemplate({ source: 'uploaded', name: parsedTemplate.fileName, title: parsedTemplate.title, total_score_x100: parsedTemplate.total_score * 100, duration_minutes: parsedTemplate.duration_minutes, sections: parsedTemplate.sections });
    onClose();
  };
  const handleApplyPreset = (template: ReferenceTemplate) => {
    onApplyTemplate({ source: 'preset', name: template.name, total_score_x100: template.total_score * 100, duration_minutes: template.duration_minutes, sections: template.sections });
    onClose();
  };
  const handleDownloadSample = () => {
    const content = `【知卷标准试卷结构模板示例】\n学段：${currentSpec.stage}\n教材：${currentSpec.textbook || '标准教材'}\n总分：100分\n考试时间：90分钟\n\n一、选择题（每题4分，共16分）\n1. [知识点1考查]\n2. [知识点2考查]\n3. [基础性质辨析]\n4. [图像规律分析]\n\n二、填空题（每题4分，共12分）\n5. [计算题填空]\n6. [性质应用填空]\n7. [规律总结填空]\n\n三、解答题（共72分）\n8. 基础解答题（15分）\n9. 几何/逻辑证明题（18分）\n10. 综合应用题（19分）\n11. 探究压轴大题（20分）\n`;
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob); const anchor = document.createElement('a');
    anchor.href = url; anchor.download = `知卷试卷结构模板参考示例_${currentSpec.subject_label || '学科'}.txt`; anchor.click(); URL.revokeObjectURL(url);
  };
  if (!isOpen) return null;
  return <ExamTemplateDialog activeTab={activeTab} setActiveTab={setActiveTab} onClose={onClose} onDownloadSample={handleDownloadSample}>
    {activeTab === 'upload' ? <ExamTemplateUploadPanel inputRef={fileInputRef} selectedFile={selectedFile} isParsing={isParsing} parseError={parseError} parsedTemplate={parsedTemplate} onFileChange={handleFileChange} onDrop={handleDrop} onRetry={(file) => void processFile(file)} onChooseAgain={() => { setParseError(null); fileInputRef.current?.click(); }} onReset={() => { setParsedTemplate(null); setSelectedFile(null); setParseError(null); }} onApply={handleApplyParsed} /> : <ExamTemplatePresetsPanel onApply={handleApplyPreset} />}
  </ExamTemplateDialog>;
};
