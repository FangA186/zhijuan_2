import React from 'react';
import { Settings, Cpu, Edit3, CheckCircle2, FileDown } from 'lucide-react';

interface StageNavProps {
  currentStage: number;
  onStageChange: (stage: number) => void;
}

const STAGES = [
  { id: 1, title: '规格与蓝图配置', desc: '学段学科与槽位分配', icon: Settings },
  { id: 2, title: '命题任务监控', desc: 'Hermes 异步流与成本', icon: Cpu },
  { id: 3, title: '三栏编辑工作台', desc: 'KaTeX渲染与独立盲解核对', icon: Edit3 },
  { id: 4, title: '质量审核门禁', desc: '硬错误拦截与人工裁决', icon: CheckCircle2 },
  { id: 5, title: '试卷历史与导出', desc: '公开投影学生卷与全解', icon: FileDown },
];

export const StageNav: React.FC<StageNavProps> = ({ currentStage, onStageChange }) => {
  return (
    <div className="bg-white border-b border-slate-200 py-3">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav aria-label="Progress">
          <ol className="flex items-center justify-between gap-2 md:gap-4 overflow-x-auto pb-1">
            {STAGES.map((stage) => {
              const Icon = stage.icon;
              const isCurrent = currentStage === stage.id;
              const isPast = currentStage > stage.id;

              return (
                <li key={stage.id} className="flex-1 min-w-[170px]">
                  <button
                    onClick={() => onStageChange(stage.id)}
                    className={`w-full flex items-center gap-3 p-2 rounded-xl text-left transition-all ${
                      isCurrent
                        ? 'bg-brand-50/80 border-2 border-brand-500 shadow-xs'
                        : isPast
                        ? 'hover:bg-slate-50 border border-transparent'
                        : 'opacity-70 hover:opacity-100 hover:bg-slate-50 border border-transparent'
                    }`}
                  >
                    <div
                      className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 font-bold text-sm ${
                        isCurrent
                          ? 'bg-brand-600 text-white shadow-sm'
                          : isPast
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {isPast ? <CheckCircle2 className="w-5 h-5 text-emerald-600" /> : <Icon className="w-5 h-5" />}
                    </div>
                    <div className="overflow-hidden">
                      <div className="flex items-center gap-1.5">
                        <span className={`text-xs font-semibold ${isCurrent ? 'text-brand-900' : 'text-slate-700'}`}>
                          {stage.title}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 truncate">{stage.desc}</p>
                    </div>
                  </button>
                </li>
              );
            })}
          </ol>
        </nav>
      </div>
    </div>
  );
};
