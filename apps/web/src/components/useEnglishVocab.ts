import { useEffect, useRef, useState } from 'react';
import { EnglishSpecConfig, TextbookVocabData, TextbookVocabImage } from '../types/spec';
import { api } from '../lib/api';

export const useEnglishVocab = (materialId: string | undefined, config: EnglishSpecConfig, onChange: (config: EnglishSpecConfig) => void) => {
  const [vocabData, setVocabData] = useState<TextbookVocabData | null>(null);
  const [isLoadingVocab, setIsLoadingVocab] = useState(false);
  const [isUploadingVocab, setIsUploadingVocab] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [previewIndex, setPreviewIndex] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const isCustomized = Boolean(config.is_vocab_customized);
  const activeImages: TextbookVocabImage[] = config.active_vocab_images != null ? config.active_vocab_images : (vocabData?.images || []);

  useEffect(() => {
    if (!materialId) { setVocabData(null); return; }
    let isMounted = true;
    setIsLoadingVocab(true);
    api.getMaterialVocab(materialId).then((data) => { if (isMounted) setVocabData(data); })
      .catch((error) => { console.warn('Failed to fetch vocab data', error); if (isMounted) setVocabData(null); })
      .finally(() => { if (isMounted) setIsLoadingVocab(false); });
    return () => { isMounted = false; };
  }, [materialId]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files?.length) return;
    setIsUploadingVocab(true);
    setUploadError(null);
    try {
      const newImages: TextbookVocabImage[] = [];
      const currentCount = activeImages.length;
      for (let index = 0; index < files.length; index++) {
        const uploaded = await api.uploadVocabImage(files[index]);
        uploaded.page_num = currentCount + index + 1;
        uploaded.order = currentCount + index + 1;
        newImages.push(uploaded);
      }
      onChange({ ...config, active_vocab_images: [...activeImages, ...newImages], is_vocab_customized: true });
    } catch (error: any) {
      console.error('Vocab upload error', error);
      setUploadError(error.message || '上传图片失败，请重试');
    } finally {
      setIsUploadingVocab(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleRemoveImage = (indexToRemove: number, event?: React.MouseEvent) => {
    event?.stopPropagation();
    const updatedList = activeImages.filter((_, index) => index !== indexToRemove);
    onChange({ ...config, active_vocab_images: updatedList, is_vocab_customized: true });
    if (previewIndex === indexToRemove) setPreviewIndex(updatedList.length ? Math.min(previewIndex, updatedList.length - 1) : null);
    else if (previewIndex !== null && previewIndex > indexToRemove) setPreviewIndex(previewIndex - 1);
  };

  const handleResetToDefault = () => {
    onChange({ ...config, active_vocab_images: undefined, is_vocab_customized: false });
    setPreviewIndex(null);
    setUploadError(null);
  };

  return { vocabData, isLoadingVocab, isUploadingVocab, uploadError, setUploadError, previewIndex, setPreviewIndex, fileInputRef, isCustomized, activeImages, handleFileUpload, handleRemoveImage, handleResetToDefault };
};
