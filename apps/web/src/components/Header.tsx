import React from 'react';
import { BookOpen, User, Shield, RefreshCw, Layers } from 'lucide-react';
import { api } from '../lib/api';

interface HeaderProps {
  currentRole: 'teacher' | 'reviewer' | 'admin';
  onRoleChange: (role: 'teacher' | 'reviewer' | 'admin') => void;
  onResetData: () => void;
  currentStage: number;
  onStageSelect: (stage: number) => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentRole,
  onRoleChange,
  onResetData,
  currentStage,
  onStageSelect,
}) => {
  const isMock = api.getMode() === 'mock';

  return (
    <header className="sticky top-0 z-30 bg-white border-b border-slate-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Left: Brand / Title */}
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => onStageSelect(1)}>
          <div className="w-10 h-10 rounded-xl bg-brand-600 text-white flex items-center justify-center shadow-md shadow-brand-500/20">
            <BookOpen className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold text-slate-900 tracking-tight">知卷</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 font-semibold border border-brand-200">
                Hermes 原创命题
              </span>
            </div>
            <p className="text-xs text-slate-500">全学段 · 严禁题库与RAG · 独立盲解验证</p>
          </div>
        </div>

        {/* Center: Stage quick navigation */}
        <div className="hidden md:flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-sm font-medium">
          {[
            { step: 1, label: '1. 规格与蓝图' },
            { step: 2, label: '2. 任务执行' },
            { step: 3, label: '3. 编辑工作台' },
            { step: 4, label: '4. 审核门禁' },
            { step: 5, label: '5. 历史与导出' },
          ].map((item) => (
            <button
              key={item.step}
              onClick={() => onStageSelect(item.step)}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                currentStage === item.step
                  ? 'bg-white text-slate-900 shadow-sm font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Right: Controls & Role Switcher */}
        <div className="flex items-center gap-3">
          {/* Mock / Live Toggle */}
          <button
            onClick={() => {
              const newMode = isMock ? 'live' : 'mock';
              api.setMode(newMode);
              window.location.reload();
            }}
            title="切换 Mock 演示模式 / 真实 API 联调模式"
            className={`text-xs px-2.5 py-1 rounded-lg border flex items-center gap-1.5 font-medium transition ${
              isMock
                ? 'bg-amber-50 text-amber-800 border-amber-300 hover:bg-amber-100'
                : 'bg-emerald-50 text-emerald-800 border-emerald-300 hover:bg-emerald-100'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>{isMock ? 'Mock演示环境' : '后端联调环境'}</span>
          </button>

          {/* Reset Demo Data */}
          <button
            onClick={onResetData}
            title="重置演练数据为初始九年级数学样卷"
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
