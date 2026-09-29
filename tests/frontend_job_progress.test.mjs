import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const srcDir = join(dirname(fileURLToPath(import.meta.url)), '..', 'apps', 'web', 'src');
const jobProgressSrc = readFileSync(join(srcDir, 'pages', 'JobProgress.tsx'), 'utf8');
const jobProgressHelpersSrc = readFileSync(join(srcDir, 'pages', 'job-progress', 'jobProgressHelpers.ts'), 'utf8');
const jobProgressStreamSrc = readFileSync(join(srcDir, 'pages', 'job-progress', 'useJobProgressStream.ts'), 'utf8');
const jobProgressHeaderSrc = readFileSync(join(srcDir, 'pages', 'job-progress', 'JobProgressHeader.tsx'), 'utf8');
const workbenchSrc = ['ExamPaperWorkbench.tsx', 'ExamPaperSingleChoice.tsx',
  'ExamPaperMultipleChoice.tsx', 'ExamPaperFillBlank.tsx', 'ExamPaperSolution.tsx']
  .map((name) => readFileSync(join(srcDir, 'pages', name === 'ExamPaperWorkbench.tsx' ? name : join('exam-paper', name)), 'utf8')).join('\n');
const statusBadgeSrc = readFileSync(join(srcDir, 'components', 'StatusBadge.tsx'), 'utf8');

test('task status enum covers all backend statuses and never collapse them into "generating"', () => {
  // 后端枚举八个状态全部在 JOB_STATUS_LABELS 中有独立中文文案，不允许 catch-all
  assert.match(jobProgressHelpersSrc, /QUEUED: '排队中'/);
  assert.match(jobProgressHelpersSrc, /RUNNING: '生成中'/);
  assert.match(jobProgressHelpersSrc, /PAUSED: '已暂停'/);
  assert.match(jobProgressHelpersSrc, /RECONCILING: '调用结果对账中'/);
  assert.match(jobProgressHelpersSrc, /COMPLETED: '任务完成，题目仍需复核'/);
  assert.match(jobProgressHelpersSrc, /PARTIAL_FAILED: '部分题目检查失败'/);
  assert.match(jobProgressHelpersSrc, /CANCELLED: '已取消'/);
  assert.match(jobProgressHelpersSrc, /FAILED: '任务失败'/);
  // 五个终态都不是“正在生成”语义，必须有终态/需处理界面
  assert.match(jobProgressHelpersSrc, /TERMINAL_STATUSES/);
  assert.match(jobProgressHelpersSrc, /['\"]FAILED['\"],\s*['\"]PARTIAL_FAILED['\"],\s*['\"]CANCELLED['\"],\s*['\"]RECONCILING['\"],\s*['\"]COMPLETED['\"]/);
});

test('ssE reconnect sequence is GET-first; never a POST start as reconnect', () => {
  // 重连路径只调用 getCurrentJob（GET 对账），不出现 startGenerationJob
  const reconnectBlock = jobProgressStreamSrc.slice(jobProgressStreamSrc.indexOf('reconcileAndSubscribe'), jobProgressStreamSrc.indexOf('handleManualReconnect'));
  assert.match(reconnectBlock, /getCurrentJob/);
  assert.doesNotMatch(reconnectBlock, /startGenerationJob|generation-jobs['\"]/);
  // 整个页面仅在用户显式操作区（本页没有开始按钮）之外不得调用 startGenerationJob
  assert.doesNotMatch(jobProgressStreamSrc, /startGenerationJob/);
  // 手动恢复也不触发 POST
  assert.match(jobProgressStreamSrc, /handleManualResubscribe[\s\S]{0,200}manualReconnectRef/);
});

test('token usage only from trusted usage field; unknown stays unknown', () => {
  assert.match(jobProgressSrc, /tokensLabelForJob/);
  assert.match(jobProgressHelpersSrc, /PARTIAL_UNKNOWN/);
  assert.match(jobProgressHelpersSrc, /部分已知/);
  assert.match(jobProgressHelpersSrc, /tokens_used == null[\s\S]{0,80}未知/);
  assert.match(jobProgressHelpersSrc, /estimated_cost_cny == null\s*\?\s*'未知'/);
  // 不允许用时间或字数估算冒充真实用量：不得从时间/时长推导 token 数值
  assert.doesNotMatch(jobProgressHelpersSrc, /tokens_used\s*=\s*[^;\n]*\b(duration|time|minute|timestamp|elapsed)\b/i);
});

test('REVIEW questions explicitly say 待教师复核; versioned single-question regenerate stays disabled', () => {
  assert.match(statusBadgeSrc, /待教师复核/);
  // 四个题型板块（单选/多选/填空/解答）各有版本化换题按钮，全部保持 disabled + 未启用文案
  const disabledRegenerate = workbenchSrc.match(/disabled[\s\S]{0,160}版本化换题尚未启用/g) || [];
  assert.equal(disabledRegenerate.length, 4);
  // 内部枚举 single_choice 等不直接显示给教师：槽位列表与聚焦区用 questionKindLabel
  assert.match(workbenchSrc, /questionKindLabel/);
});

test('teacher-facing question kind labels are Chinese names', () => {
  assert.match(jobProgressHelpersSrc, /single_choice: '单选题'/);
  assert.match(jobProgressHelpersSrc, /multiple_choice: '多选题'/);
  assert.match(jobProgressHelpersSrc, /true_false: '判断题'/);
  assert.match(jobProgressHelpersSrc, /fill_blank: '填空题'/);
  assert.match(jobProgressHelpersSrc, /solution: '解答题'/);
  assert.match(jobProgressHelpersSrc, /short_answer: '简答题'/);
  assert.match(jobProgressHelpersSrc, /essay: '论述题'/);
  assert.match(jobProgressHelpersSrc, /material_group: '材料综合题组'/);
});

test('double-click / keyboard repeat protection with single-submit lock on generation start', () => {
  // 作业页所有控制按钮在请求期间锁定（controlBusy），避免连点重复暂停/取消
  assert.match(jobProgressSrc, /controlBusy/);
  assert.match(jobProgressHeaderSrc, /disabled=\{props.controlBusy\}/);
  // 预览启动锁在启动流程（FoolproofSetup）之外，本页重新加载只 GET 当前任务（App 已完成契约）
  assert.match(workbenchSrc, /isGenerating\b/);
});
