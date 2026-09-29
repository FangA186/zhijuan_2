"""Small generated curriculum files; no private textbook downloads required."""
import json
from services.curriculum import CurriculumRepository

EDITIONS = ['人教A版', '人教B版', '北师大版', '苏教版', '沪教版', '湘教版', '鲁教版']


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False))


def material(id, edition, subject='数学', stage='高中', hidden=False):
    tags = [{'tag_id': dim + name, 'tag_dimension_id': dim, 'tag_name': name}
            for dim,name in [('zxxxd',stage),('zxxxk',subject),('zxxbb',edition)]]
    if hidden:tags.append({'tag_id':'hidden','tag_dimension_id':'hidden','tag_name':'隐藏'})
    return {'id':id,'title':f'合成教材 {edition} {subject}','tag_list':tags}


def curriculum_fixture(root):
    repo = CurriculumRepository(root / 'data')
    write(repo.tags_file, {'hierarchies':[{'hierarchy_name':'学段','ext':{'hidden_tags':['hidden']},
        'children':[{'tag_id':'zxxxd高中','tag_name':'高中'}]}]})
    rows = [material(f'fixture-{i}', ed) for i,ed in enumerate(EDITIONS)]
    rows.append(material('fixture-hidden','测试隐藏版',hidden=True))
    write(repo.mats_file, rows)
    write(repo.trees_dir / 'fixture-0.json', [{'id':'root','title':'目录','children':[
        {'id':'chapter1','title':'1.1 集合的概念','children':[]},
        {'id':'body','title':'正文','children':[]}]}])
    # This fixture is about textbook filtering, independent of the checked-in vocab index.
    repo.vocab_catalog_file = root / 'empty-vocab.json'
    repo.vocab_images_base = root / 'images'
    return repo
