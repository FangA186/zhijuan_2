import { useState } from 'react';
import { TextbookSummary } from '../types/spec';

export const useTextbookUrlImport = (materials: TextbookSummary[]) => {
  const [urlInput, setUrlInput] = useState('');
  const [urlMatchedMat, setUrlMatchedMat] = useState<TextbookSummary | null>(null);
  const [urlError, setUrlError] = useState('');
  const handleParseUrl = () => {
    setUrlError('');
    setUrlMatchedMat(null);
    if (!urlInput.trim()) return;
    let defaultTag = '';
    try {
      if (urlInput.includes('defaultTag=')) {
        const url = new URL(urlInput.startsWith('http') ? urlInput : `https://${urlInput}`);
        defaultTag = url.searchParams.get('defaultTag') || '';
      } else defaultTag = urlInput;
    } catch {
      const match = urlInput.match(/defaultTag=([^&]+)/);
      if (match) defaultTag = decodeURIComponent(match[1]);
    }
    if (!defaultTag) {
      setUrlError('未能从输入文本中解析出 defaultTag 参数，请粘贴包含课程标签的完整链接。');
      return;
    }
    const tagIds = decodeURIComponent(defaultTag).split('/').filter(Boolean);
    const match = materials.find((material) => tagIds.every((tag) => (material.tag_ids || []).includes(tag)));
    if (match) setUrlMatchedMat(match);
    else setUrlError('已提取标签组合，但在当前课本底库中未匹配到完全一致的教材（可能为尚未收录的新版实验教材）。');
  };
  return { urlInput, setUrlInput, urlMatchedMat, urlError, handleParseUrl };
};
