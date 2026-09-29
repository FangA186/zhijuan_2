import React from 'react';
import { BookOpen, User, Shield, RefreshCw, Plus, AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';
import { GenerationRuntimeState } from '../types/job';
import { reasonLabel } from '../lib/runtimeReasons';

interface HeaderProps {
  currentRole: 'teacher' | 'reviewer' | 'admin';
  onRoleChange: (role: 'teacher' | 'reviewer' | 'admin') => void;
  onResetData: () => void;
  onNewExam?: () => void;
  titleInfo?: string;
  generationState?: GenerationRuntimeState | null;
  generationChecking?: boolean;
  onRecheckGeneration?: () => void;
  showNewExamButton?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  currentRole,
  onRoleChange,
  onResetData,
  onNewExam,
  titleInfo,
  generationState,
  generationChecking = false,
  onRecheckGeneration,
  showNewExamButton = false,
}) => {
  // 生成服务状态：fail-closed。versionConfirmed=false 或 ready=null 一律视为“状态未确认”，不得误绿。
  let statusChip: { tone: 'ok' | 'error' | 'unknown' | 'checking'; text: string } | null = null;
  if (generationChecking) {
    statusChip = { tone: 'checking', text: '正在检查生成服务…' };
  } else if (!generationState || generationState.versionConfirmed !== true || generationState.ready === null) {
    statusChip = { tone: 'unknown', text: '生成服务版本/状态未确认' };
  } else if (generationState.ready === true) {
    statusChip = { tone: 'ok', text: '生成服务已就绪' };
  } else {
    const firstCode = generationState.reasonCodes[0];
    statusChip = { tone: 'error', text: firstCode ? reasonLabel(firstCode) : '生成服务未就绪' };
  }

  const statusToneClass: Record<typeof statusChip.tone, string> = {
    ok: 'bg-emerald-50 border-emerald-200/80 text-emerald-700',
    error: 'bg-rose-50 border-rose-200/80 text-rose-700',
    unknown: 'bg-slate-50 border-slate-200/80 text-slate-600',
    checking: 'bg-slate-50 border-slate-200/80 text-slate-500',
  };

  return (
    <header className="sticky top-0 z-30 bg-white border-b border-slate-200 shadow-2xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Left: Brand / Title */}
        <div className="flex items-center gap-3 cursor-pointer" onClick={onNewExam}>
          <div className="w-10 h-10 rounded-2xl bg-brand-600 text-white flex items-center justify-center shadow-sm shadow-brand-500/20">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xl font-bold text-slate-900 tracking-tight">知卷</span>
          </div>
        </div>

        {/* Center: Current Paper Title Info + Generation Service Status (separate concerns) */}
        <div className="hidden lg:flex flex-col items-start gap-1">
          {titleInfo && (
            <div className="flex items-center gap-2 px-3.5 py-1 rounded-xl bg-slate-50 border border-slate-200/80 text-xs font-semibold text-slate-700">
              <span className="w-2 h-2 rounded-full bg-slate-400" />
              <span className="truncate max-w-sm">{titleInfo}</span>
            </div>
          )}
          {statusChip && (
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-semibold ${statusToneClass[statusChip.tone]}`}>
              {statusChip.tone === 'ok' ? <CheckCircle2 className="w-3.5 h-3.5" />
                : statusChip.tone === 'error' ? <AlertTriangle className="w-3.5 h-3.5" />
                : statusChip.tone === 'checking' ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                : <RefreshCw className="w-3.5 h-3.5" />}
              <span className="truncate max-w-[13rem]">{statusChip.text}</span>
              {onRecheckGeneration && statusChip.tone !== 'ok' && (
                <button
                  type="button"
                  onClick={onRecheckGeneration}
                  title="重新检查生成服务（只读，不会发起任何生成）"
                  className="ml-1 px-1.5 py-0.5 rounded bg-white/70 border border-slate-200 hover:bg-white hover:border-brand-300 text-brand-700 transition cursor-pointer"
                >
                  <RefreshCw className="w-3 h-3" />
                </button>
              )}
            </div>
          )}
        </div>

        {/* Right: Controls & Role Switcher */}
        <div className="flex items-center gap-3">
          {import.meta.env.DEV && <a href="/project" className="text-xs font-semibold text-brand-700 hover:underline whitespace-nowrap">项目进展</a>}

          {showNewExamButton && onNewExam && (
            <button
              onClick={onNewExam}
              className="hidden sm:flex px-3.5 py-1.5 bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs rounded-xl shadow-xs transition items-center gap-1.5 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>新建试卷</span>
            </button>
          )}

          {/* Reset Demo Data */}
          <button
            onClick={onResetData}
            title="重置试卷为九年级数学示例"
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          {/* Role selector */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg text-xs font-medium text-slate-700">
            <button
              onClick={() => onRoleChange('teacher')}
              className={`px-2 py-1 rounded flex items-center gap-1 transition ${
                currentRole === 'teacher' ? 'bg-white shadow-xs text-brand-700 font-bold' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              <User className="w-3.5 h-3.5" />
              命题教师
            </button>
            <button
              onClick={() => onRoleChange('reviewer')}
              className={`px-2 py-1 rounded flex items-center gap-1 transition ${
                currentRole === 'reviewer' ? 'bg-white shadow-xs text-amber-700 font-bold' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              <Shield className="w-3.5 h-3.5" />
              审核教师
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
