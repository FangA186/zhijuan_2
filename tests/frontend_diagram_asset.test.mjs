import { after, test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const webRoot = join(root, 'apps/web');
const requireWeb = createRequire(join(webRoot, 'package.json'));
const { createServer } = await import(requireWeb.resolve('vite'));
const React = requireWeb('react');
const { renderToStaticMarkup } = requireWeb('react-dom/server');
const vite = await createServer({ root: webRoot, server: { middlewareMode: true }, appType: 'custom' });
after(() => vite.close());

const { MathRenderer } = await vite.ssrLoadModule('/src/lib/math.tsx');
const { ExportModal } = await vite.ssrLoadModule('/src/components/ExportModal.tsx');
const render = (component, props) => renderToStaticMarkup(React.createElement(component, props));

test('trusted asset id renders image; old id displays a missing-diagram error', () => {
  const alt = '算筹纵式记数：2 对应 2 根竖棒';
  const valid = render(MathRenderer, { content: [{ type: 'asset', asset_id: 'a'.repeat(64), alt }] });
  assert.match(valid, /<img src="http:\/\/localhost:8000\/v1\/exams\/current\/assets\/a{64}"/);
  assert.match(valid, /图示加载中/);
  const missing = render(MathRenderer, { content: [{ type: 'asset', asset_id: 'old-id', alt }] });
  assert.match(missing, /role="alert"[^>]*>图示缺失/);
  assert.doesNotMatch(missing, /<img/);
});

test('text and tables escape HTML while math still renders', () => {
  const html = render(MathRenderer, { content: [
    { type: 'text', text: '<img src=x onerror=alert(1)> $x^2$' },
    { type: 'table', headers: ['<script>'], rows: [['2']] },
  ] });
  assert.doesNotMatch(html, /<script>|<img src=x/);
  assert.match(html, /&lt;img src=x onerror=alert\(1\)&gt;/);
  assert.match(html, /&lt;script&gt;/);
  assert.match(html, /class="katex/);
  assert.match(html, /<table/);
});

test('a diagram anywhere in a question blocks the legacy print export', () => {
  const base = { public: { local_id: 'q1', kind: 'single_choice', prompt: [{ type: 'text', text: '题目' }],
    options: [], children: [], material_ids: [], score_x100: 100 }, private: { answers: [] } };
  const props = { isOpen: true, onClose: () => {}, spec: { title: '测试卷', total_score_x100: 100, duration_minutes: 90 } };
  const plain = render(ExportModal, { ...props, candidates: [base] });
  assert.doesNotMatch(plain, /已禁用这些导出以避免丢图/);
  const withImage = structuredClone(base);
  withImage.public.children = [{ ...structuredClone(base.public), prompt: [
    { type: 'asset', asset_id: 'a'.repeat(64), alt: '图' },
  ] }];
  const diagram = render(ExportModal, { ...props, candidates: [withImage] });
  assert.match(diagram, /已禁用这些导出以避免丢图/);
  assert.match(diagram, /disabled=""[^>]*>.*?打印 \/ 导出为 PDF/s);
});
