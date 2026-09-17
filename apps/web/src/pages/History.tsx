import React, { useState } from 'react';
import { FileDown, Plus, Clock, ShieldCheck } from 'lucide-react';
import { ExamSpec } from '../types/spec';
import { GeneratedCandidate } from '../types/candidate';
import { formatScoreX100 } from '../lib/scoring';
import { ExportModal } from '../components/ExportModal';

interface HistoryProps {
  spec: ExamSpec;
  candidates: GeneratedCandidate[];
  onNewExam: () => void;
}

export const History: React.FC<HistoryProps> = ({ spec, candidates, onNewExam }) => {
  const [isExportOpen, setIsExportOpen] = useState(false);

  // 模拟历史试卷列表
  const mockHistoryList = [
    {
      id: 'exam_demo_01',
      title: spec.title,
      stage_label: `${spec.grade_label} · ${spec.subject_label}`,
      status: 'PUBLISHED',
      total_score_x100: spec.total_score_x100,
      question_count: candidates.length,
      revision: 1,
      created_at: '2026-09-17 14:40',
      isCurrent: true,
    },
    {
      id: 'exam_hist_02',
      title: '五年级语文第一单元古诗文阅读专项调研卷',
      stage_label: '五年级 · 小学语文',
      status: 'PUBLISHED',
      total_score_x100: 10000,
      question_count: 8,
      revision: 2,
      created_at: '2026-09-16 10:20',
      isCurrent: false,
    },
    {
      id: 'exam_hist_03',
      title: '高一物理必修第一册牛顿第二定律综合测试卷',
      stage_label: '高一 · 高中物理',
      status: 'REVIEWED',
      total_score_x100: 10000,
      question_count: 12,
      revision: 1,
      created_at: '2026-09-15 16:35',
      isCurrent: false,
    },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-800">
              阶段五
            </span>
            <h1 className="text-xl font-bold text-slate-900">试卷历史与导出中心 (History & Export)</h1>
          </div>
          <p className="text-sm text-slate-500">
            支持一键导出学生版公开投影 PDF、教师全解 PDF、标准 JSON 及 Word 草稿。
          </p>
        </div>

        <button
          onClick={onNewExam}
          className="px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-sm rounded-xl flex items-center gap-2 shadow-sm transition shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>创建新试卷项目</span>
        </button>
      </div>

      {/* Security & Strict Boundary Banner */}
      <div className="p-4 bg-slate-900 text-slate-200 rounded-2xl flex items-start gap-3 text-xs leading-relaxed shadow-sm">
        <ShieldCheck className="w-5 h-5 text-brand-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold text-white">架构规范约束提示：</span>
          知卷历史试卷仅用于教师本人/本组织的【恢复、编辑、重新打印与审计】。
          系统**严禁**将历史试卷存入题库或构建向量索引，下一次生成绝不检索或抽取历史题，确保每次命题均为 Hermes 现场原创生成！
        </div>
      </div>

      {/* Exam Cards Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <h2 className="font-bold text-sm text-slate-900">本组织可访问的试卷项目</h2>
          <span className="text-xs text-slate-400">共 {mockHistoryList.length} 份试卷</span>
        </div>

        <div className="divide-y divide-slate-100">
          {mockHistoryList.map((exam) => (
            <div
              key={exam.id}
              className="p-6 hover:bg-slate-50/80 transition flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1.5">
                <div className="flex items-center gap-2.5">
                  <h3 className="font-bold text-base text-slate-900">{exam.title}</h3>
                  {exam.isCurrent && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-brand-100 text-brand-800">
                      当前工作卷
                    </span>
                  )}
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      exam.status === 'PUBLISHED'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {exam.status === 'PUBLISHED' ? '已正式发布' : '待复核'}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
                  <span className="font-medium text-slate-700">{exam.stage_label}</span>
                  <span>•</span>
                  <span>满分 {formatScoreX100(exam.total_score_x100)} 分</span>
                  <span>•</span>
                  <span>共 {exam.question_count} 道原创题目</span>
                  <span>•</span>
                  <span className="flex items-center gap-1 font-mono">
                    <Clock className="w-3.5 h-3.5" />
                    {exam.created_at}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => setIsExportOpen(true)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs rounded-xl flex items-center gap-1.5 transition"
                >
                  <FileDown className="w-4 h-4 text-brand-600" />
                  <span>导出成卷 (PDF / Word / JSON)</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Export Modal */}
      <ExportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        spec={spec}
        candidates={candidates}
      />
    </div>
  );
};
