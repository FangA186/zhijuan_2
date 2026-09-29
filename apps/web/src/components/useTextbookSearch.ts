import { useMemo, useState } from 'react';
import { TextbookSummary } from '../types/spec';

export const useTextbookSearch = (materials: TextbookSummary[]) => {
  const [searchKw, setSearchKw] = useState('');
  const searchResults = useMemo(() => {
    const query = searchKw.trim().toLowerCase();
    return query ? materials.filter((material) => material.title.toLowerCase().includes(query)).slice(0, 20) : [];
  }, [materials, searchKw]);
  return { searchKw, searchResults, handleSearch: setSearchKw };
};
