import test from 'node:test';
import assert from 'node:assert/strict';
import { stageYearFromGrade, gradeLabelForStage, subjectCodeFromLabel } from '../apps/web/src/lib/stageYear.ts';

test('textbook grade labels use years within each stage', () => {
  for (const [stage, label, year] of [
    ['primary', '小学五年级', 5],
    ['junior', '七年级', 1], ['junior', '八年级', 2], ['junior', '九年级', 3],
    ['junior', '初一', 1], ['junior', '初二', 2], ['junior', '初三', 3],
    ['senior', '高一', 1], ['senior', '高二', 2], ['senior', '高三', 3],
  ]) {
    assert.equal(stageYearFromGrade(stage, label), year, `${stage}: ${label}`);
  }
  assert.equal(stageYearFromGrade('senior', '必修第一册'), null);
  assert.equal(stageYearFromGrade('junior', '教材上册'), null);
});

test('selected years and textbook subjects keep the approved canonical values', () => {
  for (const [stage, names] of [
    ['junior', ['七年级', '八年级', '九年级']],
    ['senior', ['高一', '高二', '高三']],
  ]) {
    names.forEach((name, index) => {
      assert.equal(gradeLabelForStage(stage, index + 1), name);
      assert.equal(stageYearFromGrade(stage, name), index + 1);
    });
  }
  assert.equal(subjectCodeFromLabel('高中数学'), 'math');
  assert.equal(subjectCodeFromLabel('初中语文'), 'chinese');
  assert.equal(subjectCodeFromLabel('小学英语'), 'english');
  assert.equal(subjectCodeFromLabel('未知学科'), null);
});
