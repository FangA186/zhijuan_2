import React from 'react';
import { ScopeSwitchDialog } from './ScopeSwitchDialog';
import { TextbookSelectModal } from '../../components/TextbookSelectModal';
import { ExamTemplateModal } from '../../components/ExamTemplateModal';
import type { FoolproofSetupModel } from './FoolproofSetupModel';

export const FoolproofSetupModals: React.FC<{ model: FoolproofSetupModel }> = ({ model }) => {
  const { spec, isTextbookModalOpen, setIsTextbookModalOpen, isTemplateModalOpen, setIsTemplateModalOpen, handleSelectTextbook, handleApplyTemplate } = model;
  return (
    <>
      <ScopeSwitchDialog model={model} />
      {/* 教材选择弹窗 */}
      <TextbookSelectModal
        isOpen={isTextbookModalOpen}
        onClose={() => setIsTextbookModalOpen(false)}
        onSelect={handleSelectTextbook}
        currentMaterialId={spec.material_id}
        initialStage={spec.stage}
      />

      {/* 试卷模板与参考示例弹窗 */}
      <ExamTemplateModal
        isOpen={isTemplateModalOpen}
        onClose={() => setIsTemplateModalOpen(false)}
        onApplyTemplate={handleApplyTemplate}
        currentSpec={spec}
      />
    </>
  );
};
