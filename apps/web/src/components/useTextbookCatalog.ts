import { useEffect, useMemo, useState } from 'react';
import { Stage, TextbookSummary } from '../types/spec';
import { TextbookFilterMode } from './textbookSelectionTypes';
import { api } from '../lib/api';
import { getTextbookCatalog } from './textbookCatalog';

export const useTextbookCatalog = (isOpen: boolean, currentMaterialId: string | undefined, initialStage: Stage, filterMode: TextbookFilterMode) => {
  const [isLoading, setIsLoading] = useState(false);
  const [allMaterials, setAllMaterials] = useState<TextbookSummary[]>([]);
  const [selectedXd, setSelectedXd] = useState('');
  const [selectedNj, setSelectedNj] = useState('');
  const [selectedXk, setSelectedXk] = useState('');
  const [selectedBb, setSelectedBb] = useState('');
  const [selectedCc, setSelectedCc] = useState('');
  const hasGrade = selectedXd !== '高中' && !selectedXd.includes('高中');

  useEffect(() => { if (isOpen) void loadMaterials(); }, [isOpen, filterMode]);
  const loadMaterials = async () => {
    setIsLoading(true);
    try {
      const response = await api.getCurriculumMaterials({ mode: filterMode });
      setAllMaterials(response.items || []);
    } catch (error) { console.error(error); }
    finally { setIsLoading(false); }
  };

  const catalog = useMemo(() => getTextbookCatalog(allMaterials, selectedXd, hasGrade, selectedNj, selectedXk, selectedBb, selectedCc), [allMaterials, selectedXd, hasGrade, selectedNj, selectedXk, selectedBb, selectedCc]);
  useEffect(() => {
    if (!catalog.stageOptions.length || selectedXd) return;
    if (currentMaterialId) {
      const current = allMaterials.find((material) => material.id === currentMaterialId);
      if (current) {
        if (current.dims?.zxxxd?.name) setSelectedXd(current.dims.zxxxd.name);
        if (current.dims?.zxxnj?.name) setSelectedNj(current.dims.zxxnj.name);
        if (current.dims?.zxxxk?.name && ['语文', '数学', '英语', '地理', '生物学', '生物', '物理', '化学', '历史'].includes(current.dims.zxxxk.name)) setSelectedXk(current.dims.zxxxk.name);
        if (current.dims?.zxxbb?.name) setSelectedBb(current.dims.zxxbb.name);
        const term = current.dims?.zxxcc?.name || current.dims?.zxxnj?.name;
        if (term) setSelectedCc(term);
        return;
      }
    }
    const defaultName = initialStage === 'senior' ? '高中' : initialStage === 'primary' ? '小学' : '初中';
    setSelectedXd(catalog.stageOptions.find((option) => option === defaultName) || catalog.stageOptions[0]);
  }, [catalog.stageOptions, initialStage, currentMaterialId, allMaterials, selectedXd]);
  useEffect(() => {
    if (!hasGrade) setSelectedNj('');
    else if (catalog.gradeOptions.length && !catalog.gradeOptions.includes(selectedNj)) setSelectedNj(catalog.gradeOptions[0]);
  }, [selectedXd, hasGrade, catalog.gradeOptions]);
  useEffect(() => { if (catalog.subjectOptions.length && !catalog.subjectOptions.includes(selectedXk)) setSelectedXk(catalog.subjectOptions[0]); }, [catalog.subjectOptions, selectedXk]);
  useEffect(() => { if (catalog.editionOptions.length && !catalog.editionOptions.includes(selectedBb)) setSelectedBb(catalog.editionOptions[0]); }, [catalog.editionOptions]);
  useEffect(() => { if (catalog.termOptions.length && !catalog.termOptions.includes(selectedCc)) setSelectedCc(catalog.termOptions[0]); }, [catalog.termOptions]);

  return { isLoading, allMaterials, hasGrade, ...catalog, selectedXd, setSelectedXd, selectedNj, setSelectedNj, selectedXk, setSelectedXk, selectedBb, setSelectedBb, selectedCc, setSelectedCc };
};
