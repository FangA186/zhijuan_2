import { topicLabel } from '../../lib/topicPlanning';
import React from 'react';
import { BookOpen } from 'lucide-react';
import { GenerationJob } from '../../types/job';
import { StatusBadge } from '../../components/StatusBadge';
import { formatScoreX100 } from '../../lib/scoring';
import { questionKindLabel } from './jobProgressHelpers';

export const JobProgressSlots: React.FC<{ job: GenerationJob }> = ({ job }) => (
  <div className="lg:col-span-5 space-y-4">
    <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
      <div className="border-b border-slate-100 pb-3">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2"><BookOpen className="w-5 h-5 text-brand-600" />试卷大纲与题目出题清单</h2>
        <p className="text-xs text-slate-500 mt-1">原创命题 → 独立做题验算 → 课标大纲审核 → 题题就绪</p>
      </div>
      <div className="space-y-3 max-h-[580px] overflow-y-auto pr-1">
        {job.slots.map(slot => <div key={slot.slot_id} className="bg-slate-50/60 p-3.5 rounded-xl border border-slate-200/80 hover:border-brand-300 hover:bg-brand-50/20 transition space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2"><span className="w-6 h-6 rounded-md bg-white border border-slate-200 text-slate-700 flex items-center justify-center font-bold text-xs shadow-2xs">#{slot.order}</span>
              <span className="font-bold text-xs text-slate-900 truncate max-w-[180px]">{topicLabel(slot.target_topic)}</span>
              <span className="text-[10px] text-slate-400 shrink-0">{questionKindLabel(slot.kind)}</span>
            </div><StatusBadge status={slot.status} />
          </div>
          <div className="flex items-center justify-between text-xs text-slate-500 pt-1 border-t border-slate-200/60"><span>认知目标：{slot.cognitive_target}</span><span className="font-semibold text-brand-600">{formatScoreX100(slot.score_x100)} 分</span></div>
        </div>)}
      </div>
    </div>
  </div>
);
