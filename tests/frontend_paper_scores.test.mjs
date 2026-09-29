import test from 'node:test';
import assert from 'node:assert/strict';
import { sumGeneratedSectionScores } from '../apps/web/src/pages/exam-paper/paperScoreSummary.ts';

test('partial paper score remains distinct from its planned maximum', () => {
  const plannedMaximum = 150;
  const currentQuestions = sumGeneratedSectionScores([36, 12, 12, 68]);
  assert.equal(currentQuestions, 128);
  assert.equal(plannedMaximum, 150);
  assert.notEqual(currentQuestions, plannedMaximum);
});
