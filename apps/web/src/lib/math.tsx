import React, { useMemo } from 'react';
import katex from 'katex';
import { Block } from '../types/candidate';

interface MathRendererProps {
  content: string | Block[];
  className?: string;
  blockDisplay?: boolean;
}

/**
 * 将含有 $...$ 或 $$...$$ 的文本转换为 KaTeX HTML
 */
function renderMixedText(text: string): string {
  if (!text) return '';

  // 匹配 $$...$$ 块级公式
  let result = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, math) => {
    try {
      return katex.renderToString(math.trim(), { displayMode: true, throwOnError: false });
    } catch {
      return `<code>$$${math}$$</code>`;
    }
  });

  // 匹配 $...$ 行内公式
  result = result.replace(/\$([^\$\n]+?)\$/g, (_, math) => {
    try {
      return `<span class="katex-inline">${katex.renderToString(math.trim(), { displayMode: false, throwOnError: false })}</span>`;
    } catch {
      return `<code>$${math}$</code>`;
    }
  });

  return result;
}

export const MathRenderer: React.FC<MathRendererProps> = ({ content, className = '', blockDisplay = false }) => {
  const renderedContent = useMemo(() => {
    if (typeof content === 'string') {
      return renderMixedText(content);
    }

    if (Array.isArray(content)) {
      return content.map((block) => {
        if (block.type === 'text') {
          return renderMixedText(block.text);
        } else if (block.type === 'math') {
          try {
            return katex.renderToString(block.latex, {
              displayMode: blockDisplay,
              throwOnError: false,
            });
          } catch {
            return `<code>$${block.latex}$</code>`;
          }
        } else if (block.type === 'table') {
          const headerHtml = `<tr>${block.headers.map((h) => `<th class="border border-slate-300 px-3 py-1 bg-slate-100 font-medium text-slate-700">${renderMixedText(h)}</th>`).join('')}</tr>`;
          const rowsHtml = block.rows
            .map((r) => `<tr>${r.map((c) => `<td class="border border-slate-300 px-3 py-1 text-slate-700">${renderMixedText(c)}</td>`).join('')}</tr>`)
            .join('');
          return `<div class="my-2 overflow-x-auto"><table class="border-collapse border border-slate-300 text-sm w-full">${headerHtml}${rowsHtml}</table></div>`;
        } else if (block.type === 'asset') {
          return `<div class="my-2 p-3 border border-slate-200 rounded bg-slate-50 text-xs text-slate-500 flex items-center gap-2"><span class="font-medium text-slate-700">[图示: ${block.alt || block.asset_id}]</span></div>`;
        }
        return '';
      }).join(' ');
    }

    return '';
  }, [content, blockDisplay]);

  return (
    <div
      className={`leading-relaxed text-slate-800 ${className}`}
      dangerouslySetInnerHTML={{ __html: renderedContent }}
    />
  );
};
