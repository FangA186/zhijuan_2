"""Basic local verification only, NOT full OpenAPI certification or SQL execution."""
from pathlib import Path
import json, re
import yaml
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parent

def load(path):
    text=path.read_text(encoding='utf-8')
    return yaml.safe_load(text) if path.suffix in ('.yaml','.yml') else json.loads(text)

def resolve_pointer(doc, fragment):
    current=doc
    if not fragment: return current
    if not fragment.startswith('/'):
        raise ValueError('Only JSON pointer fragments supported in this check')
    for part in fragment[1:].split('/'):
        key=part.replace('~1','/').replace('~0','~')
        current=current[int(key)] if isinstance(current,list) else current[key]
    return current

def check_refs(node, document_path):
    if isinstance(node,dict):
        ref=node.get('$ref')
        if ref:
            file_name, _, fragment=ref.partition('#')
            target=(document_path.parent/file_name).resolve() if file_name else document_path
            if not target.is_relative_to(ROOT): raise ValueError('Unexpected remote or external ref')
            resolve_pointer(load(target),fragment)
        for v in node.values(): check_refs(v,document_path)
    elif isinstance(node,list):
        for v in node: check_refs(v,document_path)

def main():
    for p in (ROOT/'contracts').glob('*.schema.json'):
        data=load(p);Draft202012Validator.check_schema(data);check_refs(data,p)
    api_path=ROOT/'contracts/openapi.yaml';api=load(api_path)
    assert api['openapi']=='3.1.0'
    check_refs(api,api_path)
    operations=set()
    for path,item in api['paths'].items():
        for method,op in item.items():
            if method not in ('get','post','put','patch','delete'): continue
            assert op['operationId'] not in operations
            operations.add(op['operationId'])
            declared={p['name'] for p in op.get('parameters',[]) if isinstance(p,dict) and p.get('in')=='path'}
            assert set(re.findall(r'\{([^}]+)\}',path))==declared
            assert 'responses' in op
    for p in (ROOT/'configs').glob('*.yaml'): load(p)
    load(ROOT/'infra/compose.yaml')
    print(f'PASS: 5 JSON Schemas, local references, {len(operations)} core operations, YAML parsing.')
    print('NOT RUN: full OpenAPI spec validator, PostgreSQL migration, live Hermes, model quality or production security tests.')

if __name__=='__main__': main()
