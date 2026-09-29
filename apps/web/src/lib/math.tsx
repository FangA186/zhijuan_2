import React, { useState } from 'react';
import katex from 'katex';
import { Block } from '../types/candidate';

interface MathRendererProps {
  content: string | Block[];
  className?: string;
  blockDisplay?: boolean;
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/v1').replace(/\/+$/, '');
const ASSET_ID_PATTERN = /^[0-9a-f]{64}$/;

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char]!);
}

/** 将普通文本转义，只把公式交给 KaTeX 生成 HTML。 */
function renderMixedText(text: string): string {
  if (!text) return '';

  const formula = /\$\$([\s\S]+?)\$\$|\$([^$\n]+?)\$/g;
  let result = '';
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = formula.exec(text))) {
    result += escapeHtml(text.slice(lastIndex, match.index));
    try {
      result += katex.renderToString((match[1] || match[2]).trim(), {
        displayMode: match[1] !== undefined,
        throwOnError: false,
        trust: false,
      });
    } catch {
      result += `<code>${escapeHtml(match[0])}</code>`;
    }
    lastIndex = formula.lastIndex;
  }

  return result + escapeHtml(text.slice(lastIndex));
}

function renderTable(block: Extract<Block, { type: 'table' }>): string {
  const headerHtml = `<tr>${block.headers.map((header) => `<th class="border border-slate-300 px-3 py-1 bg-slate-100 font-medium text-slate-700">${renderMixedText(header)}</th>`).join('')}</tr>`;
  const rowsHtml = block.rows.map((row) => `<tr>${row.map((cell) => `<td class="border border-slate-300 px-3 py-1 text-slate-700">${renderMixedText(cell)}</td>`).join('')}</tr>`).join('');
  return `<div class="my-2 overflow-x-auto"><table class="border-collapse border border-slate-300 text-sm w-full">${headerHtml}${rowsHtml}</table></div>`;
}

const MissingAsset: React.FC<{ label: string }> = ({ label }) => (
  <div role="alert" className="my-2 border border-red-300 bg-red-50 p-3 text-sm text-red-800">
    图示缺失：{label}
  </div>
);

const DiagramAsset: React.FC<{ assetId: string; alt: string }> = ({ assetId, alt }) => {
  const [state, setState] = useState<'loading' | 'loaded' | 'missing'>('loading');
  const label = alt || '未标记图示';

  if (!ASSET_ID_PATTERN.test(assetId)) return <MissingAsset label={label} />;
  if (state === 'missing') return <MissingAsset label={label} />;

  return (
    <figure className="relative my-2">
      {state === 'loading' && <span role="status" className="text-sm text-slate-600">图示加载中：{label}</span>}
      <img
        src={`${API_BASE_URL}/exams/current/assets/${assetId}`}
        alt={label}
        className={state === 'loaded' ? 'max-w-full h-auto' : 'absolute h-px w-px opacity-0'}
        onLoad={() => setState('loaded')}
        onError={() => setState('missing')}
      />
      {state === 'loaded' && <figcaption className="text-xs text-slate-600">{label}</figcaption>}
    </figure>
  );
};

export const MathRenderer: React.FC<MathRendererProps> = ({ content, className = '', blockDisplay = false }) => {
  if (typeof content === 'string') {
    return <div className={`leading-relaxed text-slate-800 ${className}`} dangerouslySetInnerHTML={{ __html: renderMixedText(content) }} />;
  }

  if (!Array.isArray(content)) return <div className={`leading-relaxed text-slate-800 ${className}`} />;

  return (
    <div className={`leading-relaxed text-slate-800 ${className}`}>
      {content.map((block, index) => {
        let rendered: React.ReactNode = null;
        if (block.type === 'text') {
          rendered = <span dangerouslySetInnerHTML={{ __html: renderMixedText(block.text) }} />;
        } else if (block.type === 'math') {
          try {
            rendered = <span dangerouslySetInnerHTML={{ __html: katex.renderToString(block.latex, { displayMode: blockDisplay, throwOnError: false, trust: false }) }} />;
          } catch {
            rendered = <code>{`$${block.latex}$`}</code>;
          }
        } else if (block.type === 'table') {
          rendered = <div dangerouslySetInnerHTML={{ __html: renderTable(block) }} />;
        } else if (block.type === 'asset') {
          rendered = <DiagramAsset key={block.asset_id} assetId={block.asset_id} alt={block.alt} />;
        }

        return <React.Fragment key={index}>{rendered}{index < content.length - 1 ? ' ' : null}</React.Fragment>;
      })}
    </div>
  );
};
