import { ArrowRight, RefreshCw, Sparkles } from 'lucide-react';
import { ExamBlueprint } from '../../types/spec';

interface Props {
  blueprint: ExamBlueprint | null;
  isGeneratingBlueprint: boolean;
  scoreBalanced: boolean;
  hasSectionIssues: boolean;
  canConfirm: boolean;
  onRefreshReadiness: () => void;
  onGenerateBlueprint: () => void;
  onConfirm: () => void;
}

export function ExamSetupHeader({
  blueprint, isGeneratingBlueprint, scoreBalanced, hasSectionIssues, canConfirm,
  onRefreshReadiness, onGenerateBlueprint, onConfirm,
}: Props) {
  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-brand-100 text-brand-800">阶段一</span>
          <h1 className="text-xl font-bold text-slate-900">命题规格定义与蓝图规划 (ExamSpec & Blueprint)</h1>
        </div>
        <p className="text-sm text-slate-500">
          按教学范围、知识点及考查目标组织，模型调用前严格执行总分矛盾拦截与分值配平。
        </p>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <button
          type="button"
          onClick={onRefreshReadiness}
          className="px-3 py-2 text-xs text-brand-600 hover:text-brand-700 font-medium flex items-center gap-1 cursor-pointer border border-brand-200 rounded-lg"
        >
          <RefreshCw className="w-3.5 h-3.5" /> 重新检查生成服务
        </button>
        <button
          onClick={onGenerateBlueprint}
          disabled={isGeneratingBlueprint || !scoreBalanced || hasSectionIssues}
          className="px-4 py-2.5 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-300 text-white font-bold text-sm rounded-xl flex items-center gap-2 shadow-xs transition"
        >
          <Sparkles className="w-4 h-4 text-amber-300" />
          {isGeneratingBlueprint ? '正在规划槽位...' : '重新生成蓝图槽位'}
        </button>
        {blueprint && (
          <button
            onClick={onConfirm}
            disabled={!canConfirm}
            className="px-5 py-2.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-sm rounded-xl flex items-center gap-2 shadow-sm transition"
          >
            <span>确认蓝图并开始命题</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}
