import React, { useState, useEffect, useMemo } from 'react';
import { X, Search, Link as LinkIcon, BookOpen, Check, Layers } from 'lucide-react';
import { TextbookSummary, Stage } from '../types/spec';
import { api } from '../lib/api';

interface TextbookSelectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (material: TextbookSummary) => void;
  currentMaterialId?: string;
  initialStage?: Stage;
}

const XD_ORDER = ['小学', '初中', '高中', '小学（五•四学制）', '初中（五•四学制）'];

const NJ_ORDER = [
  '一年级', '二年级', '三年级', '四年级', '五年级', '六年级',
  '七年级', '八年级', '九年级',
  '一至二年级', '三至四年级', '五至六年级', '学生读本'
];

const XK_ORDER = [
  '语文', '数学', '英语',
  '道德与法治', '思想政治',
  '科学', '物理', '化学', '生物学',
  '历史', '地理',
  '体育与健康', '信息技术', '通用技术',
  '音乐', '美术', '艺术', '艺术·音乐', '艺术·美术',
  '劳动', '俄语', '日语', '法语', '德语', '西班牙语',
  '心理健康', '综合实践活动'
];

const BB_ORDER = [
  '人教版', '人教A版', '人教版（B版）（主编：高存明）', '人教B版',
  '统编版', '北师大版', '苏教版', '沪教版', '鄂教版', '湘教版',
  '人教鄂教版', '冀教版', '北京版', '青岛版', '教科版', '湘科版',
  '粤教科技版', '大象社版', '西南大学版', '鲁科版', '鲁人版',
  '人音版', '人美版', '苏少版'
];

const CC_ORDER = [
  '上册', '下册', '全一册',
  '必修 第一册', '必修 第二册', '必修 第三册',
  '必修1', '必修2', '必修3', '必修4', '必修5',
  '选择性必修 第一册', '选择性必修 第二册', '选择性必修 第三册',
  '选择性必修1', '选择性必修2', '选择性必修3',
  '选修 第一册', '选修 第二册', '选修 第三册'
];

export const TextbookSelectModal: React.FC<TextbookSelectModalProps> = ({
  isOpen,
  onClose,
  onSelect,
  currentMaterialId,
  initialStage = 'junior',
}) => {
  const [activeTab, setActiveTab] = useState<'cascade' | 'url' | 'search'>('cascade');
  const [filterMode, setFilterMode] = useState<'visible' | 'all'>('visible');
  const [isLoading, setIsLoading] = useState(false);
  const [allMaterials, setAllMaterials] = useState<TextbookSummary[]>([]);

  // 级联选择状态
  const [selectedXd, setSelectedXd] = useState<string>('');
  const [selectedNj, setSelectedNj] = useState<string>('');
  const [selectedXk, setSelectedXk] = useState<string>('');
  const [selectedBb, setSelectedBb] = useState<string>('');
  const [selectedCc, setSelectedCc] = useState<string>('');

  // 搜索 Tab
  const [searchKw, setSearchKw] = useState('');
  const [searchResults, setSearchResults] = useState<TextbookSummary[]>([]);

  // URL Tab
  const [urlInput, setUrlInput] = useState('');
  const [urlMatchedMat, setUrlMatchedMat] = useState<TextbookSummary | null>(null);
  const [urlError, setUrlError] = useState('');

  // 加载全量或可见底册
  useEffect(() => {
    if (!isOpen) return;
    loadMaterials();
  }, [isOpen, filterMode]);

  const loadMaterials = async () => {
    setIsLoading(true);
    try {
      const res = await api.getCurriculumMaterials({ mode: filterMode });
      setAllMaterials(res.items || []);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  // 区分学段是否含有年级（高中无年级）
  const hasGrade = useMemo(() => {
    return selectedXd !== '高中' && !selectedXd.includes('高中');
  }, [selectedXd]);

  // 可选学段列表
  const stageOptions = useMemo(() => {
    const set = new Set<string>();
    allMaterials.forEach((m) => {
      const name = m.dims?.zxxxd?.name;
      if (name) set.add(name);
    });
    return Array.from(set).sort((a, b) => {
      let ia = XD_ORDER.indexOf(a);
      let ib = XD_ORDER.indexOf(b);
      if (ia === -1) ia = 999;
      if (ib === -1) ib = 999;
      return ia - ib;
    });
  }, [allMaterials]);

  // 初始化选择学段
  useEffect(() => {
    if (stageOptions.length === 0) return;
    if (!selectedXd) {
      const defaultName =
        initialStage === 'senior' ? '高中' : initialStage === 'primary' ? '小学' : '初中';
      const matched = stageOptions.find((o) => o === defaultName) || stageOptions[0];
      setSelectedXd(matched);
    }
  }, [stageOptions, initialStage]);

  // 可选年级列表（高中自动清空）
  const gradeOptions = useMemo(() => {
    if (!hasGrade) return [];
    const set = new Set<string>();
    allMaterials
      .filter((m) => m.dims?.zxxxd?.name === selectedXd)
      .forEach((m) => {
        const name = m.dims?.zxxnj?.name;
        if (name) set.add(name);
      });
    return Array.from(set).sort((a, b) => {
      let ia = NJ_ORDER.indexOf(a);
      let ib = NJ_ORDER.indexOf(b);
      if (ia === -1) ia = 999;
      if (ib === -1) ib = 999;
      return ia - ib;
    });
  }, [allMaterials, selectedXd, hasGrade]);

  // 当学段改变时重置年级
  useEffect(() => {
    if (!hasGrade) {
      setSelectedNj('');
    } else if (gradeOptions.length > 0 && !gradeOptions.includes(selectedNj)) {
      setSelectedNj(gradeOptions[0]);
    }
  }, [selectedXd, hasGrade, gradeOptions]);

  // 可选学科列表
  const subjectOptions = useMemo(() => {
    const set = new Set<string>();
    allMaterials
      .filter((m) => {
        if (m.dims?.zxxxd?.name !== selectedXd) return false;
        if (hasGrade && selectedNj && m.dims?.zxxnj?.name !== selectedNj) return false;
        return true;
      })
      .forEach((m) => {
        const name = m.dims?.zxxxk?.name;
        if (name) set.add(name);
      });
    return Array.from(set).sort((a, b) => {
      let ia = XK_ORDER.indexOf(a);
      let ib = XK_ORDER.indexOf(b);
      if (ia === -1) ia = 999;
      if (ib === -1) ib = 999;
      return ia - ib;
    });
  }, [allMaterials, selectedXd, hasGrade, selectedNj]);

  useEffect(() => {
    if (subjectOptions.length > 0 && !subjectOptions.includes(selectedXk)) {
      setSelectedXk(subjectOptions[0]);
    }
  }, [subjectOptions]);

  // 可选版本列表
  const editionOptions = useMemo(() => {
    const set = new Set<string>();
    allMaterials
      .filter((m) => {
        if (m.dims?.zxxxd?.name !== selectedXd) return false;
        if (hasGrade && selectedNj && m.dims?.zxxnj?.name !== selectedNj) return false;
        if (m.dims?.zxxxk?.name !== selectedXk) return false;
        return true;
      })
      .forEach((m) => {
        const name = m.dims?.zxxbb?.name;
        if (name) set.add(name);
      });
    return Array.from(set).sort((a, b) => {
      let ia = BB_ORDER.indexOf(a);
      let ib = BB_ORDER.indexOf(b);
      if (ia === -1) ia = 999;
      if (ib === -1) ib = 999;
      return ia - ib;
    });
  }, [allMaterials, selectedXd, hasGrade, selectedNj, selectedXk]);

  useEffect(() => {
    if (editionOptions.length > 0 && !editionOptions.includes(selectedBb)) {
      setSelectedBb(editionOptions[0]);
    }
  }, [editionOptions]);

  // 可选册次列表
  const termOptions = useMemo(() => {
    const set = new Set<string>();
    allMaterials
      .filter((m) => {
        if (m.dims?.zxxxd?.name !== selectedXd) return false;
        if (hasGrade && selectedNj && m.dims?.zxxnj?.name !== selectedNj) return false;
        if (m.dims?.zxxxk?.name !== selectedXk) return false;
        if (m.dims?.zxxbb?.name !== selectedBb) return false;
        return true;
      })
      .forEach((m) => {
        const name = m.dims?.zxxcc?.name || m.dims?.zxxnj?.name;
        if (name) set.add(name);
      });
    return Array.from(set).sort((a, b) => {
      let ia = CC_ORDER.indexOf(a);
      let ib = CC_ORDER.indexOf(b);
      if (ia === -1) ia = 999;
      if (ib === -1) ib = 999;
      return ia - ib;
    });
  }, [allMaterials, selectedXd, hasGrade, selectedNj, selectedXk, selectedBb]);

  useEffect(() => {
    if (termOptions.length > 0 && !termOptions.includes(selectedCc)) {
      setSelectedCc(termOptions[0]);
    }
  }, [termOptions]);

  // 级联匹配到的教材
  const matchedMaterials = useMemo(() => {
    return allMaterials.filter((m) => {
      if (m.dims?.zxxxd?.name !== selectedXd) return false;
      if (hasGrade && selectedNj && m.dims?.zxxnj?.name !== selectedNj) return false;
      if (m.dims?.zxxxk?.name !== selectedXk) return false;
      if (m.dims?.zxxbb?.name !== selectedBb) return false;
      const cc = m.dims?.zxxcc?.name || m.dims?.zxxnj?.name;
      if (cc !== selectedCc) return false;
      return true;
    });
  }, [allMaterials, selectedXd, hasGrade, selectedNj, selectedXk, selectedBb, selectedCc]);

  // 处理快速搜索
  const handleSearch = (kw: string) => {
    setSearchKw(kw);
    if (!kw.trim()) {
      setSearchResults([]);
      return;
    }
    const k = kw.trim().toLowerCase();
    const results = allMaterials.filter((m) => m.title.toLowerCase().includes(k)).slice(0, 20);
    setSearchResults(results);
  };

  // 处理 URL 粘贴解析
  const handleParseUrl = () => {
    setUrlError('');
    setUrlMatchedMat(null);
    if (!urlInput.trim()) return;

    let defaultTag = '';
    try {
      if (urlInput.includes('defaultTag=')) {
        const urlObj = new URL(urlInput.startsWith('http') ? urlInput : 'https://' + urlInput);
        defaultTag = urlObj.searchParams.get('defaultTag') || '';
      } else {
        defaultTag = urlInput;
      }
    } catch {
      const m = urlInput.match(/defaultTag=([^&]+)/);
      if (m) defaultTag = decodeURIComponent(m[1]);
    }

    if (!defaultTag) {
      setUrlError('未能从输入文本中解析出 defaultTag 参数，请粘贴包含课程标签的完整链接。');
      return;
    }

    const decoded = decodeURIComponent(defaultTag);
    const tagIds = decoded.split('/').filter(Boolean);

    const match = allMaterials.find((m) => {
      const matTags = m.tag_ids || [];
      return tagIds.every((tid) => matTags.includes(tid));
    });

    if (match) {
      setUrlMatchedMat(match);
    } else {
      setUrlError('已提取标签组合，但在当前课本底库中未匹配到完全一致的教材（可能为尚未收录的新版实验教材）。');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white w-full max-w-4xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-brand-100 text-brand-700 flex items-center justify-center font-bold">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <div className="text-base font-bold text-slate-900 flex items-center gap-2">
                <span>选择国家标准教材 (国家中小学智慧教育平台)</span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">
                  {filterMode === 'visible' ? '官网开放 1727 本' : '全库 3209 本'}
                </span>
              </div>
              <div className="text-xs text-slate-500">
                严格遵循国家课程标准与智慧教育平台导航体系，选定教材后将自动同步试卷规格并加载章节目录树
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Tabs & Filter Mode Switcher */}
        <div className="px-6 py-2.5 border-b border-slate-200 flex items-center justify-between bg-white gap-4 flex-wrap">
          <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl">
            <button
              onClick={() => setActiveTab('cascade')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                activeTab === 'cascade' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>级联筛选 (学段/学科/版本)</span>
            </button>
            <button
              onClick={() => setActiveTab('search')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                activeTab === 'search' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Search className="w-3.5 h-3.5" />
              <span>关键字快速搜书</span>
            </button>
            <button
              onClick={() => setActiveTab('url')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                activeTab === 'url' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <LinkIcon className="w-3.5 h-3.5" />
              <span>粘贴网页 URL 解析</span>
            </button>
          </div>

          {/* Mode Switcher */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-xs font-medium">
            <button
              onClick={() => setFilterMode('visible')}
              className={`px-2.5 py-1 rounded-lg transition ${
                filterMode === 'visible' ? 'bg-emerald-600 text-white font-bold shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              🟢 仅看官网开放
            </button>
            <button
              onClick={() => setFilterMode('all')}
              className={`px-2.5 py-1 rounded-lg transition ${
                filterMode === 'all' ? 'bg-indigo-600 text-white font-bold shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              🌐 显示全库全部 (3209)
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {/* TAB 1: 级联筛选 */}
          {activeTab === 'cascade' && (
            <div className="space-y-6">
              {/* Cascade Selectors Grid */}
              <div
                className={`grid gap-3 transition-all ${
                  hasGrade ? 'grid-cols-2 sm:grid-cols-5' : 'grid-cols-2 sm:grid-cols-4'
                }`}
              >
                {/* 1. 学段 */}
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1.5">1. 学段</label>
                  <select
                    value={selectedXd}
                    onChange={(e) => setSelectedXd(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-2.5 py-2 text-xs font-medium text-slate-800 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
                  >
                    {stageOptions.map((xd) => (
                      <option key={xd} value={xd}>
                        {xd}
                      </option>
                    ))}
                  </select>
                </div>

                {/* 2. 年级 (高中时自动彻底隐藏) */}
                {hasGrade && (
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1.5">2. 年级</label>
                    <select
                      value={selectedNj}
                      onChange={(e) => setSelectedNj(e.target.value)}
                      className="w-full border border-slate-300 rounded-lg px-2.5 py-2 text-xs font-medium text-slate-800 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
                    >
                      {gradeOptions.map((nj) => (
                        <option key={nj} value={nj}>
                          {nj}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* 3. 学科 */}
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1.5">
                    {hasGrade ? '3. 学科' : '2. 学科'}
                  </label>
                  <select
                    value={selectedXk}
                    onChange={(e) => setSelectedXk(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-2.5 py-2 text-xs font-medium text-slate-800 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
                  >
                    {subjectOptions.map((xk) => (
                      <option key={xk} value={xk}>
                        {xk}
                      </option>
                    ))}
                  </select>
                </div>

                {/* 4. 版本 */}
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1.5">
                    {hasGrade ? '4. 版本' : '3. 版本'}
                  </label>
                  <select
                    value={selectedBb}
                    onChange={(e) => setSelectedBb(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-2.5 py-2 text-xs font-medium text-slate-800 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
                  >
                    {editionOptions.map((bb) => (
                      <option key={bb} value={bb}>
                        {bb}
                      </option>
                    ))}
                  </select>
                </div>

                {/* 5. 册次 */}
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1.5">
                    {hasGrade ? '5. 册次' : '4. 册次'}
                  </label>
                  <select
                    value={selectedCc}
                    onChange={(e) => setSelectedCc(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-2.5 py-2 text-xs font-medium text-slate-800 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
                  >
                    {termOptions.map((cc) => (
                      <option key={cc} value={cc}>
                        {cc}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Matched Result Area */}
              <div className="border-t border-slate-200 pt-5">
                <div className="text-xs font-bold text-slate-600 uppercase tracking-wider mb-3">
                  当前维度匹配结果 (共 {matchedMaterials.length} 本教材)
                </div>

                {isLoading ? (
                  <div className="p-8 text-center text-slate-500 text-sm">正在加载教材库...</div>
                ) : matchedMaterials.length === 0 ? (
                  <div className="p-8 text-center text-slate-400 border border-dashed border-slate-300 rounded-xl text-sm">
                    当前组合暂无对应教材，可切换为【全库全部】模式或调整筛选条件。
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {matchedMaterials.map((mat) => {
                      const isSelected = mat.id === currentMaterialId;
                      const isNew = mat.title.includes('新教材');
                      const thumbSrc = mat.thumb || `http://localhost:8000/v1/curriculum/covers/${mat.id}.jpg`;

                      return (
                        <div
                          key={mat.id}
                          className={`p-4 rounded-xl border transition flex gap-3.5 items-start ${
                            isSelected
                              ? 'border-brand-600 bg-brand-50/50 ring-2 ring-brand-500/20'
                              : 'border-slate-200 hover:border-slate-300 bg-white shadow-xs'
                          }`}
                        >
                          <img
                            src={thumbSrc}
                            alt="cover"
                            referrerPolicy="no-referrer"
                            className="w-16 h-22 object-cover rounded-md border border-slate-200 shrink-0 shadow-xs bg-slate-100"
                            onError={(e) => {
                              (e.target as HTMLElement).style.display = 'none';
                            }}
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5 flex-wrap mb-1">
                              {isNew ? (
                                <span className="px-1.5 py-0.5 rounded-sm bg-emerald-100 text-emerald-800 font-bold text-[10px]">
                                  新教材
                                </span>
                              ) : (
                                <span className="px-1.5 py-0.5 rounded-sm bg-slate-100 text-slate-600 font-medium text-[10px]">
                                  原版/旧版
                                </span>
                              )}
                              {mat.isVisible ? (
                                <span className="px-1.5 py-0.5 rounded-sm bg-emerald-50 text-emerald-700 font-semibold text-[10px] border border-emerald-200">
                                  🟢 官网开放
                                </span>
                              ) : (
                                <span
                                  className="px-1.5 py-0.5 rounded-sm bg-amber-50 text-amber-800 font-semibold text-[10px] border border-amber-200 flex items-center gap-0.5"
                                  title={mat.visReason}
                                >
                                  🔒 官网隐藏
                                </span>
                              )}
                            </div>

                            <div className="font-bold text-sm text-slate-900 leading-snug line-clamp-2">
                              {mat.title}
                            </div>
                            <div className="text-[11px] font-mono text-slate-400 mt-1 truncate">
                              ID: {mat.id}
                            </div>

                            {!mat.isVisible && (
                              <div className="text-[10px] text-amber-700 mt-1.5 bg-amber-50 p-1 rounded-sm border border-amber-100">
                                原因: {mat.visReason}
                              </div>
                            )}

                            <div className="mt-3">
                              <button
                                onClick={() => {
                                  onSelect(mat);
                                  onClose();
                                }}
                                className="px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-lg transition shadow-xs flex items-center gap-1.5"
                              >
                                <Check className="w-3.5 h-3.5" />
                                <span>确认选用此教材</span>
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: 关键字快速搜索 */}
          {activeTab === 'search' && (
            <div className="space-y-4">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="text"
                  value={searchKw}
                  onChange={(e) => handleSearch(e.target.value)}
                  placeholder="输入教材名称、学科或版本搜索，例如：数学必修第一册、物理八年级、统编版语文..."
                  className="w-full pl-9 pr-4 py-2.5 border border-slate-300 rounded-xl text-sm text-slate-800 focus:ring-2 focus:ring-brand-500 focus:outline-hidden"
                />
              </div>

              <div className="space-y-2">
                <div className="text-xs text-slate-500">
                  {searchKw ? `搜索结果（最多展示 20 本）：` : '请输入搜索词查找教材...'}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {searchResults.map((mat) => (
                    <div
                      key={mat.id}
                      className="p-3 border border-slate-200 hover:border-slate-300 rounded-xl bg-white shadow-xs flex items-center justify-between gap-3"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="font-bold text-xs text-slate-900 truncate">{mat.title}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5 truncate">
                          {mat.dims?.zxxxd?.name} · {mat.dims?.zxxxk?.name} · {mat.dims?.zxxbb?.name}
                        </div>
                      </div>
                      <button
                        onClick={() => {
                          onSelect(mat);
                          onClose();
                        }}
                        className="px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-lg shrink-0 transition"
                      >
                        选用
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: 粘贴 URL 解析 */}
          {activeTab === 'url' && (
            <div className="space-y-4">
              <p className="text-xs text-slate-600">
                支持直接粘贴国家中小学智慧教育平台（<code>basic.smartedu.cn</code>）课程链接，智能解析 <code>defaultTag</code> 标签链并锁定教材：
              </p>

              <div className="flex gap-2">
                <input
                  type="text"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="如：https://basic.smartedu.cn/syncClassroom?defaultTag=e7bbcefe-0590-11ed...%2F5036342972"
                  className="flex-1 px-3 py-2 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-brand-500 focus:outline-hidden font-mono"
                />
                <button
                  onClick={handleParseUrl}
                  className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-xl transition shrink-0"
                >
                  解析并匹配
                </button>
              </div>

              {urlError && (
                <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700">
                  {urlError}
                </div>
              )}

              {urlMatchedMat && (
                <div className="p-4 rounded-xl border border-emerald-300 bg-emerald-50/50 flex items-center justify-between gap-4">
                  <div>
                    <div className="text-xs font-bold text-emerald-800 mb-1">🎉 成功解析并匹配到国家教材：</div>
                    <div className="text-sm font-bold text-slate-900">{urlMatchedMat.title}</div>
                    <div className="text-xs text-slate-500 font-mono mt-0.5">ID: {urlMatchedMat.id}</div>
                  </div>
                  <button
                    onClick={() => {
                      onSelect(urlMatchedMat);
                      onClose();
                    }}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-xs transition shrink-0"
                  >
                    确认选用该教材
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-200 bg-slate-50/50 flex items-center justify-between text-xs text-slate-500">
          <div>💡 选择教材后，知卷将自动解析教材体系并加载其全册官方章节目录树。</div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 border border-slate-300 hover:bg-slate-100 rounded-lg text-slate-700 font-semibold transition"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
};
