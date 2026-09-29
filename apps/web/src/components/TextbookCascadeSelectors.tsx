import React from 'react';

interface TextbookCascadeSelectorsProps {
  hasGrade: boolean;
  stageOptions: string[];
  gradeOptions: string[];
  subjectOptions: string[];
  editionOptions: string[];
  termOptions: string[];
  selectedXd: string;
  selectedNj: string;
  selectedXk: string;
  selectedBb: string;
  selectedCc: string;
  setSelectedXd: (value: string) => void;
  setSelectedNj: (value: string) => void;
  setSelectedXk: (value: string) => void;
  setSelectedBb: (value: string) => void;
  setSelectedCc: (value: string) => void;
}

export const TextbookCascadeSelectors: React.FC<TextbookCascadeSelectorsProps> = (props) => {
  const selectClass = 'w-full border border-slate-300 rounded-lg px-2.5 py-2 text-xs font-medium text-slate-800 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-hidden';
  const { hasGrade } = props;
  return (
    <div className={`grid gap-3 transition-all ${hasGrade ? 'grid-cols-2 sm:grid-cols-5' : 'grid-cols-2 sm:grid-cols-4'}`}>
      <div><label className="block text-xs font-semibold text-slate-600 mb-1.5">1. 学段</label><select value={props.selectedXd} onChange={(event) => props.setSelectedXd(event.target.value)} className={selectClass}>{props.stageOptions.map((value) => <option key={value} value={value}>{value}</option>)}</select></div>
      {hasGrade && <div><label className="block text-xs font-semibold text-slate-600 mb-1.5">2. 年级</label><select value={props.selectedNj} onChange={(event) => props.setSelectedNj(event.target.value)} className={selectClass}>{props.gradeOptions.map((value) => <option key={value} value={value}>{value}</option>)}</select></div>}
      <div><label className="block text-xs font-semibold text-slate-600 mb-1.5">{hasGrade ? '3. 学科' : '2. 学科'}</label><select value={props.selectedXk} onChange={(event) => props.setSelectedXk(event.target.value)} className={selectClass}>{props.subjectOptions.map((value) => <option key={value} value={value}>{value === '生物学' ? '生物' : value}</option>)}</select></div>
      <div><label className="block text-xs font-semibold text-slate-600 mb-1.5">{hasGrade ? '4. 版本' : '3. 版本'}</label><select value={props.selectedBb} onChange={(event) => props.setSelectedBb(event.target.value)} className={selectClass}>{props.editionOptions.map((value) => <option key={value} value={value}>{value}</option>)}</select></div>
      <div><label className="block text-xs font-semibold text-slate-600 mb-1.5">{hasGrade ? '5. 册次' : '4. 册次'}</label><select value={props.selectedCc} onChange={(event) => props.setSelectedCc(event.target.value)} className={selectClass}>{props.termOptions.map((value) => <option key={value} value={value}>{value}</option>)}</select></div>
    </div>
  );
};
