import React from 'react';
import { EnglishSpecConfig } from '../types/spec';
import { EnglishVocabPanel } from './EnglishVocabPanel';
import { EnglishVocabGrid } from './EnglishVocabGrid';
import { EnglishVocabLightbox } from './EnglishVocabLightbox';
import { useEnglishVocab } from './useEnglishVocab';

export const EnglishVocabGallery: React.FC<{ materialId?: string; config: EnglishSpecConfig; onChange: (config: EnglishSpecConfig) => void }> = ({ materialId, config, onChange }) => {
  const vocab = useEnglishVocab(materialId, config, onChange);
  const requestUpload = () => vocab.fileInputRef.current?.click();
  return (
    <>
      <input type="file" ref={vocab.fileInputRef} multiple accept="image/jpeg,image/png,image/webp" className="hidden" onChange={vocab.handleFileUpload} />
      <EnglishVocabPanel vocabData={vocab.vocabData} isLoading={vocab.isLoadingVocab} isCustomized={vocab.isCustomized} imageCount={vocab.activeImages.length} isUploading={vocab.isUploadingVocab} uploadError={vocab.uploadError} onUpload={requestUpload} onReset={vocab.handleResetToDefault} onClearError={() => vocab.setUploadError(null)}>
        <EnglishVocabGrid images={vocab.activeImages} vocabData={vocab.vocabData} isUploading={vocab.isUploadingVocab} onPreview={vocab.setPreviewIndex} onRemove={vocab.handleRemoveImage} onUpload={requestUpload} onReset={vocab.handleResetToDefault} />
      </EnglishVocabPanel>
      <EnglishVocabLightbox previewIndex={vocab.previewIndex} images={vocab.activeImages} vocabData={vocab.vocabData} setPreviewIndex={vocab.setPreviewIndex} onRemove={vocab.handleRemoveImage} />
    </>
  );
};
