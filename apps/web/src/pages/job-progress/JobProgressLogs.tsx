import React from 'react';
import { GenerationJob } from '../../types/job';
import { AgentActivityConsole } from './AgentActivityConsole';
interface Props { job: GenerationJob; onGoToEditor: () => void; isCompleted: boolean; isTerminal: boolean; }
export const JobProgressLogs: React.FC<Props> = ({ job, onGoToEditor, isTerminal }) => (
  <div className="lg:col-span-7 min-w-0 space-y-3">
    <AgentActivityConsole logs={job.logs} terminal={isTerminal} status={`已处理 ${job.completed_slots}/${job.total_slots} 题`} />
    {isTerminal && <button onClick={onGoToEditor} className="w-full rounded-xl bg-brand-600 p-3 text-white">查看已生成的题目</button>}
  </div>
);
