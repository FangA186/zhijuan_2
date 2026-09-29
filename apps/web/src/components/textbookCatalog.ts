import { TextbookSummary } from '../types/spec';

const XD_ORDER = ['小学', '初中', '高中', '小学（五•四学制）', '初中（五•四学制）'];
const NJ_ORDER = ['一年级', '二年级', '三年级', '四年级', '五年级', '六年级', '七年级', '八年级', '九年级', '一至二年级', '三至四年级', '五至六年级', '学生读本'];
const ALLOWED_XK = ['语文', '数学', '英语', '地理', '生物学', '生物', '物理', '化学', '历史'];
const BB_ORDER = ['人教版', '人教A版', '人教版（B版）（主编：高存明）', '人教B版', '统编版', '北师大版', '苏教版', '沪教版', '鄂教版', '湘教版', '人教鄂教版', '冀教版', '北京版', '青岛版', '教科版', '湘科版', '粤教科技版', '大象社版', '西南大学版', '鲁科版', '鲁人版', '人音版', '人美版', '苏少版'];
const CC_ORDER = ['上册', '下册', '全一册', '必修 第一册', '必修 第二册', '必修 第三册', '必修1', '必修2', '必修3', '必修4', '必修5', '选择性必修 第一册', '选择性必修 第二册', '选择性必修 第三册', '选择性必修1', '选择性必修2', '选择性必修3', '选修 第一册', '选修 第二册', '选修 第三册'];

const ordered = (values: Set<string>, order: string[]) => Array.from(values).sort((a, b) => {
  const left = order.indexOf(a), right = order.indexOf(b);
  return (left < 0 ? 999 : left) - (right < 0 ? 999 : right);
});
const dimensions = (material: TextbookSummary) => material.dims;
const gradeMatches = (material: TextbookSummary, stage: string, hasGrade: boolean, grade: string) =>
  dimensions(material)?.zxxxd?.name === stage && (!hasGrade || !grade || dimensions(material)?.zxxnj?.name === grade);

export const getTextbookCatalog = (all: TextbookSummary[], stage: string, hasGrade: boolean, grade: string, subject: string, edition: string, term: string) => {
  const stageValues = new Set<string>();
  all.forEach((material) => { const name = dimensions(material)?.zxxxd?.name; if (name) stageValues.add(name); });
  const stageOptions = ordered(stageValues, XD_ORDER);
  const gradeValues = new Set<string>();
  all.filter((material) => dimensions(material)?.zxxxd?.name === stage).forEach((material) => {
    const name = dimensions(material)?.zxxnj?.name; if (name) gradeValues.add(name);
  });
  const gradeOptions = hasGrade ? ordered(gradeValues, NJ_ORDER) : [];
  const subjectValues = new Set<string>();
  all.filter((material) => gradeMatches(material, stage, hasGrade, grade)).forEach((material) => {
    const name = dimensions(material)?.zxxxk?.name; if (name && ALLOWED_XK.includes(name)) subjectValues.add(name);
  });
  const subjectOptions = ordered(subjectValues, ALLOWED_XK);
  const editionValues = new Set<string>();
  all.filter((material) => gradeMatches(material, stage, hasGrade, grade) && dimensions(material)?.zxxxk?.name === subject).forEach((material) => {
    const name = dimensions(material)?.zxxbb?.name; if (name) editionValues.add(name);
  });
  const editionOptions = ordered(editionValues, BB_ORDER);
  const termValues = new Set<string>();
  all.filter((material) => gradeMatches(material, stage, hasGrade, grade) && dimensions(material)?.zxxxk?.name === subject && dimensions(material)?.zxxbb?.name === edition).forEach((material) => {
    const name = dimensions(material)?.zxxcc?.name || dimensions(material)?.zxxnj?.name; if (name) termValues.add(name);
  });
  const termOptions = ordered(termValues, CC_ORDER);
  const matchedMaterials = all.filter((material) => gradeMatches(material, stage, hasGrade, grade)
    && dimensions(material)?.zxxxk?.name === subject && dimensions(material)?.zxxbb?.name === edition
    && (dimensions(material)?.zxxcc?.name || dimensions(material)?.zxxnj?.name) === term);
  return { stageOptions, gradeOptions, subjectOptions, editionOptions, termOptions, matchedMaterials };
};
