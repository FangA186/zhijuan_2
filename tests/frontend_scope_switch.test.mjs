import test from 'node:test';
import assert from 'node:assert/strict';
import { applyScopeSwitch, markTopicSources } from '../apps/web/src/lib/sectionScope.ts';

test('both switch choices invalidate confirmation and clear never removes manual topics', (t) => {
  const storage = new Map();
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: {
    getItem: key => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
  } });
  t.after(() => delete globalThis.localStorage);
  const scope = { topics: ['教材章', '模板题', '手动项'], scope_confirmed: true };
  markTopicSources('switch-test', ['教材章'], 'textbook');
  markTopicSources('switch-test', ['模板题'], 'template');
  markTopicSources('switch-test', ['手动项'], 'manual');
  const cleared = applyScopeSwitch(scope, 'clear', 'switch-test');
  const kept = applyScopeSwitch(scope, 'keep', 'switch-test');
  assert.deepEqual(cleared.topics, ['手动项']);
  assert.deepEqual(kept.topics, scope.topics);
  assert.equal(cleared.scope_confirmed, false);
  assert.equal(kept.scope_confirmed, false);
  assert.equal(scope.scope_confirmed, true);
  assert.equal(scope.topics.length, 3);
});
