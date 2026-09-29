import React from 'react';
import { FileDown, Printer } from 'lucide-react';
import { ExamSpec } from '../../types/spec';
import { GeneratedCandidate } from '../../types/candidate';
import { ExportModal } from '../../components/ExportModal';
import type { ExamPaperSectionProps } from './ExamPaperSectionProps';
import { sumGeneratedSectionScores } from './paperScoreSummary';
import { ExamPaperSingleChoice } from './ExamPaperSingleChoice';
import { ExamPaperMultipleChoice } from './ExamPaperMultipleChoice';
import { ExamPaperFillBlank } from './ExamPaperFillBlank';
import { ExamPaperSolution } from './ExamPaperSolution';

interface Props {
  spec: ExamSpec; candidates: GeneratedCandidate[]; viewMode: 'student' | 'teacher';
  onViewModeChange: (mode: 'student' | 'teacher') => void; onPrint: () => void;
  paperTitle: string; onPaperTitleChange: (title: string) => void;
  totalScore: string; isExportOpen: boolean; onExportOpenChange: (open: boolean) => void;
  sectionProps: ExamPaperSectionProps;
}

export const ExamPaperPrintView: React.FC<Props> = props => {
  const { multipleChoiceQuestions, singleChoiceTotal, multipleChoiceTotal, fillBlankTotal, solutionTotal } = props.sectionProps;
  const { spec, candidates, viewMode, totalScore, paperTitle, isExportOpen, sectionProps } = props;
  const generatedTotal = sumGeneratedSectionScores([singleChoiceTotal, multipleChoiceTotal, fillBlankTotal, solutionTotal]);
  return (
    <div className="min-h-screen bg-slate-100/70 pb-24">
      {/* 顶部固定悬浮操作栏（打印时隐藏） */}
      <div className="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b border-slate-200/80 shadow-xs px-4 sm:px-8 py-3 print:hidden">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          {/* 左侧：试卷类型切换（学生测试卷 vs 教师全解卷） */}
          <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs font-semibold">
            <button
              type="button"
              onClick={() => props.onViewModeChange('student')}
              className={`px-3.5 py-1.5 rounded-lg transition-all flex items-center gap-1.5 cursor-pointer ${
                viewMode === 'student'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span>📄 学生作答卷 (纯净版)</span>
            </button>
            <button
              type="button"
              onClick={() => props.onViewModeChange('teacher')}
              className={`px-3.5 py-1.5 rounded-lg transition-all flex items-center gap-1.5 cursor-pointer ${
                viewMode === 'teacher'
                  ? 'bg-brand-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span>📝 教师详解卷 (含解析与采分点)</span>
            </button>
          </div>

          {/* 右侧：打印与导出行动区 */}
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={props.onPrint}
              className="px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs rounded-xl border border-slate-300 shadow-2xs transition flex items-center gap-1.5 cursor-pointer"
              title="直接调起浏览器 A4 打印预览"
            >
              <Printer className="w-4 h-4 text-slate-600" />
              <span>直接打印</span>
            </button>

            <button
              type="button"
              onClick={() => props.onExportOpenChange(true)}
              className="px-3.5 py-2 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-xs transition flex items-center gap-1.5 cursor-pointer"
            >
              <FileDown className="w-4 h-4" />
              <span>导出试卷 (PDF/Word)</span>
            </button>
          </div>
        </div>
      </div>

      <p className="mx-auto mt-4 max-w-4xl px-4 text-sm text-amber-800 print:hidden">
        题目检查状态来自服务端记录；任务完成或答案一致不代表检查通过。教师使用前请逐题复核。
      </p>

      {/* A4 试卷主体容器 */}
      <div className="max-w-4xl mx-auto mt-6 px-4 print:p-0 print:m-0 print:max-w-none">
        <div className="bg-white border border-slate-300 shadow-sm p-8 sm:p-14 rounded-sm print:border-none print:shadow-none print:p-0 print:rounded-none space-y-8 text-slate-900 leading-relaxed font-serif">
          {/* 卷头密封线与考场信息 */}
          <div className="border-b-2 border-slate-900 pb-3 text-xs font-sans flex flex-wrap items-center justify-between gap-2 text-slate-600">
            <div className="font-bold text-slate-800">
              绝密★启用前 · {spec.grade_label}{spec.subject_label}
            </div>
            <div className="flex items-center gap-4">
              <span>班级：___________</span>
              <span>姓名：___________</span>
              <span>考号：___________</span>
              <span>考场/座位：___________</span>
            </div>
          </div>

          {/* 试卷大标题（点击可编辑） */}
          <div className="text-center space-y-2 pt-2">
            <input
              type="text"
              value={paperTitle}
              onChange={(e) => props.onPaperTitleChange(e.target.value)}
              className="w-full text-center text-xl sm:text-2xl font-bold text-slate-900 bg-transparent border-b border-transparent hover:border-slate-300 focus:border-brand-500 focus:outline-hidden py-1 tracking-wide"
              title="点击可直接修改试卷大标题"
            />
            <div className="text-xs text-slate-500 font-sans flex items-center justify-center gap-4">
              <span>本卷共 {candidates.length} 小题</span>
              <span>计划满分：{totalScore} 分</span>
              <span>考试时间：{spec.duration_minutes} 分钟</span>
            </div>
          </div>

          {/* 考生须知与动态得分栏 */}
          <div className="grid grid-cols-1 sm:grid-cols-12 gap-4 items-center font-sans">
            <div className="sm:col-span-7 p-3 rounded-lg border border-slate-300 bg-slate-50/50 text-[11px] text-slate-600 space-y-0.5">
              <div className="font-bold text-slate-800">考生须知：</div>
              <div>1. 答卷前，请务必将自己的班级、姓名、考号填写在密封线内指定位置。</div>
              <div>2. 必须在答题卡或预留作答区域内书写，字迹工整、卷面整洁。</div>
            </div>

            {/* 得分板表格（动态根据包含的大题板块计算） */}
            <div className="sm:col-span-5 border border-slate-400 text-center text-xs">
              <div
                className={`grid ${
                  multipleChoiceQuestions.length > 0 ? 'grid-cols-5' : 'grid-cols-4'
                } bg-slate-100 border-b border-slate-300 font-bold py-1`}
              >
                <div>一</div>
                {multipleChoiceQuestions.length > 0 && <div>二</div>}
                <div>{multipleChoiceQuestions.length > 0 ? '三' : '二'}</div>
                <div>{multipleChoiceQuestions.length > 0 ? '四' : '三'}</div>
                <div>当前题目合计</div>
              </div>
              <div
                className={`grid ${
                  multipleChoiceQuestions.length > 0 ? 'grid-cols-5' : 'grid-cols-4'
                } py-2 font-bold text-slate-700`}
              >
                <div>{singleChoiceTotal}</div>
                {multipleChoiceQuestions.length > 0 && <div>{multipleChoiceTotal}</div>}
                <div>{fillBlankTotal}</div>
                <div>{solutionTotal}</div>
                <div>{generatedTotal}</div>
              </div>
              <div className="border-t border-slate-300 py-1 text-[10px] text-slate-600">计划满分：{totalScore} 分</div>
            </div>
          </div>

          <ExamPaperSingleChoice {...sectionProps} />
          <ExamPaperMultipleChoice {...sectionProps} />
          <ExamPaperFillBlank {...sectionProps} />
          <ExamPaperSolution {...sectionProps} />
          {/* 卷尾印刷署名 */}
          <div className="pt-8 border-t border-slate-300 text-center text-xs text-slate-400 font-sans flex items-center justify-between">
            <span>知卷 · 智能原创命题系统</span>
            <span>教师使用前请复核题目、答案与适用范围</span>
            <span>第 1 页 (全卷完)</span>
          </div>
        </div>
      </div>

      {/* 导出试卷弹窗 */}
      <ExportModal
        isOpen={isExportOpen}
        onClose={() => props.onExportOpenChange(false)}
        spec={spec}
        candidates={candidates}
      />
    </div>
  );
};
