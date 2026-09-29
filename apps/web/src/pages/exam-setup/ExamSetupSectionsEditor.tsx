import { Dispatch, SetStateAction } from 'react';
import { MultipleChoiceScoringField } from '../../components/MultipleChoiceScoringField';
import { Plus, Trash2 } from 'lucide-react';
import { ExamSection, ExamSpec, QuestionKind } from '../../types/spec';
import { formatScoreX100, parseScoreToX100 } from '../../lib/scoring';

interface Props {
  spec: ExamSpec;
  setSpec: Dispatch<SetStateAction<ExamSpec | null>>;
}

export function ExamSetupSectionsEditor({ spec, setSpec }: Props) {
  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-brand-500"></span>
          3. 大题题型与分值配平 (Sections)
        </h2>
        <button
          type="button"
          onClick={() => {
            const newSection: ExamSection = {
              id: `sec_${Date.now()}`, title: '新增大题题组', question_type: 'short_answer',
              count: 2, score_each_x100: 500, topics: ['核心考查点'],
            };
            setSpec({ ...spec, sections: [...spec.sections, newSection] });
          }}
          className="px-3 py-1 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg flex items-center gap-1"
        >
          <Plus className="w-3.5 h-3.5" />添加题型大组
        </button>
      </div>

      <MultipleChoiceScoringField spec={spec} setSpec={setSpec} />
      <div className="space-y-3">
        {spec.sections.map((section, index) => (
          <div key={section.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <input type="text" value={section.title} onChange={(event) => {
                const updated = [...spec.sections];
                updated[index].title = event.target.value;
                setSpec({ ...spec, sections: updated });
              }} className="font-bold text-sm bg-transparent border-b border-transparent hover:border-slate-300 focus:border-brand-500 focus:bg-white focus:outline-hidden px-1 py-0.5 flex-1" />
              <button onClick={() => setSpec({ ...spec, sections: spec.sections.filter((_, i) => i !== index) })}
                className="text-slate-400 hover:text-rose-600 p-1"><Trash2 className="w-4 h-4" /></button>
            </div>

            <div className="grid grid-cols-3 gap-3 text-xs">
              <div>
                <label className="text-slate-500 mb-1 block">题型</label>
                <select value={section.question_type} onChange={(event) => {
                  const updated = [...spec.sections];
                  updated[index].question_type = event.target.value as QuestionKind;
                  setSpec({ ...spec, sections: updated });
                }} className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5">
                  <option value="single_choice">单项选择题</option>
                  <option value="multiple_choice">多项选择题</option>
                  <option value="true_false">判断题</option>
                  <option value="fill_blank">填空题</option>
                  <option value="solution">计算解答题</option>
                  <option value="short_answer">简答题</option>
                  <option value="essay">作文/论述题</option>
                </select>
              </div>
              <div>
                <label className="text-slate-500 mb-1 block">题量 (道)</label>
                <input type="number" min="1" max="50" value={section.count} onChange={(event) => {
                  const updated = [...spec.sections];
                  updated[index].count = parseInt(event.target.value) || 1;
                  setSpec({ ...spec, sections: updated });
                }} className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5" />
              </div>
              <div>
                <label className="text-slate-500 mb-1 block">每题分值 (分)</label>
                <input type="number" step="0.5" min="1" value={formatScoreX100(section.score_each_x100)}
                  onChange={(event) => {
                    const updated = [...spec.sections];
                    updated[index].score_each_x100 = parseScoreToX100(event.target.value);
                    setSpec({ ...spec, sections: updated });
                  }} className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
