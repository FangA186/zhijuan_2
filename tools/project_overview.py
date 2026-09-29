#!/usr/bin/env python3
"""只读项目资料投影：不加载应用配置，不调用模型，不返回任意文件正文。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.memory_lib import ROOT, evidence_state, handoff_time, now, redact, safe_path

from tools.project_overview_files import browsable, data, describe, document, references, related, tree
from tools.bug_records import bug_snapshot


def snapshot(root: Path) -> dict:
    ledger=data(root,'progress/features.yaml'); work=data(root,'progress/work.yaml')
    plan=data(root,'execution/task-index.yaml')['tasks']+data(root,'progress/extra-tasks.yaml')['tasks']
    guide=data(root,'progress/file-guide.yaml'); warnings=[]
    try:
        bugs = bug_snapshot(root)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
        bugs = {'items': [], 'database_url': ''}
        warnings.append('Bug 记录无效，请运行 tools/bug_memory.py check 核对，未将失败当作空库通过。')
    features=[]
    for feature in ledger['features']:
        state,reason=evidence_state(root,feature)
        features.append({**feature,'verification':state,'verification_reason':reason})
    tasks=[]
    for task in plan:
        actual=work.get('tasks',{}).get(task['id'],{})
        tasks.append({k:task.get(k,[]) for k in ('id','title','phase','depends_on','target_files','implementation_steps','verification')} | {'status':actual.get('status','NOT_STARTED'),'note':actual.get('review_note','尚无实际状态登记。' if not actual else ''),'evidence_refs':actual.get('evidence_refs',[]),'previous_completion_claim':actual.get('previous_completion_claim'), 'source':'progress/work.yaml' if actual else '未登记（原任务模板）'})
    handoffs=[]
    for p in sorted((root/'progress/handoffs').glob('*.yaml')):
        rel=p.relative_to(root).as_posix()
        try:
            h=data(root,rel)
            paths=[s for s in h.get('scope_patterns',[]) if s.startswith(('apps/','services/','tools/','tests/','contracts/','progress/','quality/'))]
            linked=[]
            for f in features:
                if h.get('task_id') in f['task_ids']:
                    linked.append({'id':f['id'],'basis':'同任务检查点（不保证覆盖功能全部内容）'})
                elif any(f['id'] in related(s,[f]) for s in paths):
                    linked.append({'id':f['id'],'basis':'实现路径关联（不等于该功能发布）'})
            handoffs.append({k:h.get(k,[]) for k in ('task_id','session_id','created_at','summary','next_action','completed','pending','decisions','failed_approaches','evidence_refs')} | {'path':rel,'commit':h.get('git',{}).get('head'),'features':linked})
        except (OSError,ValueError,yaml.YAMLError): warnings.append('交接解析失败：'+rel)
    handoffs.sort(key=lambda h:handoff_time(h.get('created_at')),reverse=True)
    for feature in features:
        # Task receipts are useful progress, but never replace the complete feature gate.
        refs = [ref for task in tasks if task['id'] in feature['task_ids'] for ref in task['evidence_refs']]
        refs += [ref for h in handoffs if h['task_id'] in feature['task_ids'] for ref in h['evidence_refs']]
        registered = []
        for ref in sorted(set(refs)):
            if not isinstance(ref, str) or not ref.startswith('acceptance-runs/'):
                continue
            try:
                p = safe_path(root, ref, must_exist=True)
                if p.is_file() and p.suffix in {'.json', '.yaml', '.yml', '.md'}:
                    registered.append(ref)
            except (OSError, ValueError):
                continue
        feature['stage_evidence_refs'] = registered
    reports=[]
    for p in sorted((root/'acceptance-runs').rglob('report.json')):
        rel=p.relative_to(root).as_posix()
        try:
            r=data(root,rel)
            reports.append({'path':rel,'date':r.get('ended_at') or r.get('started_at'),'overall':r.get('overall','UNKNOWN'),'features':r.get('requested_features',[]),'application_executed':r.get('application_executed',False),'live_model_called':r.get('live_model_called',False),'results':[{'id':v.get('id'),'status':v.get('status'),'exit_code':v.get('exit_code'),'tests':(v.get('unit_summary') or {}).get('tests_run')} for v in r.get('results',[])]})
        except (OSError,ValueError,yaml.YAMLError): warnings.append('报告解析失败：'+rel)
    reports.sort(key=lambda r:str(r['date'] or ''),reverse=True)
    def git(*args: str) -> str:
        r=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True,timeout=8)
        return r.stdout.strip() if r.returncode==0 else ''
    try:
        head=git('rev-parse','HEAD'); branch=git('branch','--show-current')
        def history(*paths: str) -> list[dict]:
            return [dict(zip(('commit','date','title'),line.split('\t',2))) for line in git('log','-8','--format=%H%x09%cI%x09%s','--',*paths).splitlines() if len(line.split('\t',2))==3]
        commits=history()
        for feature in features:
            paths=feature.get('implementation_paths',[])
            feature['commits']=history(*paths) if paths else []
    except (OSError,subprocess.TimeoutExpired): head='';branch='';commits=[];warnings.append('Git 信息不可用，未推断版本。')
    bundle=data(root,'docs/archive/v1.4-bundle/BUNDLE_INFO.json')
    return {'bugs':bugs,'generated_at':now(),'branch':branch or 'NO_GIT','head':head,'stage':work['stage_hint'],'next_task':work['recommended_next_task'],'versions':{'bundle':bundle.get('bundle_version'),'product':bundle.get('product_documents_version'),'frontend':data(root,'apps/web/package.json').get('version')},'features':features,'tasks':tasks,'handoffs':handoffs,'reports':reports,'commits':commits,'references':references(root,guide),'warnings':warnings,'directories':[{'path':p.name,'description':describe(p.name,True,guide)[0],'expandable':browsable(root,p.name)} for p in sorted(root.iterdir()) if p.is_dir() and not p.is_symlink()]}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['snapshot','tree','document']);parser.add_argument('--path',default='');parser.add_argument('--offset',type=int,default=0);parser.add_argument('--query',default='')
    args=parser.parse_args()
    try:
        result=snapshot(ROOT) if args.mode=='snapshot' else tree(ROOT,args.path,args.offset,args.query) if args.mode=='tree' else document(ROOT,args.path)
        # Redact string values before JSON encoding, so replacements cannot corrupt JSON.
        def clean(value):
            if isinstance(value,str): return redact(value)
            if isinstance(value,list): return [clean(v) for v in value]
            if isinstance(value,dict): return {k:clean(v) for k,v in value.items()}
            return value
        print(json.dumps(clean(result),ensure_ascii=False,default=str))
        return 0
    except (OSError,ValueError,KeyError,TypeError,yaml.YAMLError):
        print(json.dumps({'error':'资料读取失败：路径受限、数据缺失或格式错误。请查看原记录。'},ensure_ascii=False))
        return 1

if __name__=='__main__':
    raise SystemExit(main())
