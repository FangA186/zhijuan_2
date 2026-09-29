import test from 'node:test';
import assert from 'node:assert/strict';
import { alignSectionTopics } from '../apps/web/src/lib/sectionScope.ts';

test('stale section topics cannot widen the teacher-selected scope or mutate the original', () => {
  const sections = [{ id: 'one', topics: ['旧范围'] }, { id: 'two', topics: ['已选B', '旧范围'] }];
  const result = alignSectionTopics(sections, ['已选A', '已选B']);
  assert.deepEqual(result.map(s => s.topics), [['已选A', '已选B'], ['已选B']]);
  assert.deepEqual(sections[0].topics, ['旧范围']);
  assert.deepEqual(alignSectionTopics(sections, []).map(s => s.topics), [[], []]);
});
