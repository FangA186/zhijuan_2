"""Safe, read-only file navigation for the local project overview."""
from __future__ import annotations

import fnmatch
import json
from pathlib import Path
import re

import yaml

from tools.memory_lib import redact, safe_path, unsafe_name

PROTECTED = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.runtime', 'dist', 'dist-ssr', '.pytest_cache'}
DOC_ROOTS = {'docs', 'execution', 'contracts', 'configs', 'database', 'infra', 'install', 'skills', 'quality', '.github'}
ROOT_DOCS = {'AGENTS.md', 'README.md'}
PROGRESS_DOCS = {'features.yaml', 'work.yaml', 'current.md', 'extra-tasks.yaml', 'policy.yaml', 'file-guide.yaml', 'README.md'}
TEXT_SUFFIXES = {'.md', '.yaml', '.yml', '.json', '.sql'}


def data(root: Path, path: str) -> dict:
    p = safe_path(root, path, must_exist=True)
    if p.stat().st_size > 2_000_000:
        raise ValueError('记录过大，未加载：' + path)
    text = p.read_text(encoding='utf-8')
    value = json.loads(text) if p.suffix == '.json' else yaml.load(text, Loader=getattr(yaml, 'CSafeLoader', yaml.SafeLoader))
    if not isinstance(value, dict):
        raise ValueError('记录应为对象：' + path)
    return value


def blocked(path: str) -> bool:
    parts = Path(path).parts
    return unsafe_name(path) or any(p in PROTECTED for p in parts)


def browsable(root: Path, path: str) -> bool:
    try:
        return not blocked(path) and safe_path(root, path, must_exist=True).is_dir()
    except (OSError, ValueError):
        return False


def readable(root: Path, path: str) -> bool:
    try:
        p = safe_path(root, path, must_exist=True)
        parts = Path(path).parts
        allowed = path in ROOT_DOCS or (parts[0] in DOC_ROOTS and p.suffix in TEXT_SUFFIXES)
        allowed |= parts[0] == 'progress' and (len(parts) == 2 and parts[1] in PROGRESS_DOCS or len(parts) > 2 and parts[1] in {'templates', 'bugs'})
        return bool(allowed and not blocked(path) and p.is_file() and p.stat().st_size <= 160_000)
    except (OSError, ValueError):
        return False


def describe(path: str, is_dir: bool, guide: dict) -> tuple[str, str]:
    lookup = guide.get('directories' if is_dir else 'files', {})
    if path in lookup:
        return lookup[path], '已整理'
    p = Path(path)
    if blocked(path):
        return '环境、凭据、依赖或生成文件；只显示用途，不读取内部内容。', '受限'
    if is_dir:
        parent = next((guide['directories'][str(x)] for x in p.parents if str(x) in guide.get('directories', {})), '')
        return (f'「{p.name}」分类目录。{parent}' if parent else '未登记用途的目录，请结合父级说明核对。'), '按路径推断'
    if p.name == '__init__.py':
        return 'Python 包入口与导出声明。', '按命名推断'
    if p.name.startswith('test_'):
        return f'针对 {p.stem[5:]} 的测试文件；是否离线需检查实际调用。', '按命名推断'
    if p.name == 'SKILL.md':
        return f'{p.parent.name} 角色的生产流程与输入输出约定。', '按路径推断'
    if path.startswith('progress/handoffs/'):
        return '任务会话交接：已做、未做、决定与证据；属于历史声明。', '按路径推断'
    if path.startswith('acceptance-runs/'):
        return '某次运行的报告、证据或日志；未逐文件审阅，正文不开放。', '按路径推断'
    suffixes = {'.tsx':'React 页面或组件', '.ts':'TypeScript 类型或逻辑', '.py':'Python 模块或开发脚本', '.json':'结构化数据或配置', '.yaml':'结构化配置或记录', '.yml':'结构化配置或 CI', '.md':'Markdown 说明文档', '.css':'页面样式', '.html':'HTML 页面或交付文档', '.sql':'SQL 定义或草案', '.docx':'Word 文档/试卷资料', '.jpg':'图片资源', '.png':'图片资源', '.webp':'图片资源', '.pdf':'PDF 资源', '.sh':'Shell 操作脚本'}
    return f'{suffixes.get(p.suffix, "辅助文件")}：{p.name}。具体职责尚未登记。', '按命名推断'


def related(path: str, features: list[dict]) -> list[str]:
    return [f['id'] for f in features if any(path == p or path.startswith(p.rstrip('/') + '/') for p in f.get('implementation_paths', [])) or any(fnmatch.fnmatchcase(path, p) for p in f.get('watch_paths', []))]


def tree(root: Path, path: str = '', offset: int = 0, query: str = '') -> dict:
    root = root.resolve()
    if offset < 0:
        raise ValueError('分页位置无效')
    if path and not browsable(root, path):
        raise ValueError('该目录不可展开')
    directory = safe_path(root, path, must_exist=True) if path else root
    guide = data(root, 'progress/file-guide.yaml')
    features = data(root, 'progress/features.yaml')['features']
    children = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold()))
    if query:
        children = [p for p in children if query.casefold() in p.name.casefold()]
    entries = []
    for p in children[offset:offset+150]:
        rel = p.relative_to(root).as_posix()
        is_dir = p.is_dir() and not p.is_symlink()
        desc, source = describe(rel, is_dir, guide)
        entries.append({'path':rel, 'name':p.name, 'is_dir':is_dir, 'description':desc, 'description_source':source, 'expandable':is_dir and browsable(root, rel), 'readable':readable(root, rel), 'restricted':blocked(rel) or p.is_symlink(), 'size':p.lstat().st_size if not is_dir else None, 'features':related(rel, features)})
    return {'path':path, 'entries':entries, 'total':len(children), 'offset':offset, 'next_offset':offset+150 if offset+150<len(children) else None}


def document(root: Path, path: str) -> dict:
    if not readable(root, path):
        raise ValueError('只允许查看已开放的开发文档；不读取源码、凭据、上传资源或原始日志')
    text = safe_path(root, path, must_exist=True).read_text(encoding='utf-8')
    return {'path':path, 'content':redact(text), 'notice':'文本只读；历史文档中的状态以当前功能账本为准。'}


def references(root: Path, guide: dict) -> list[dict]:
    agents = safe_path(root, 'AGENTS.md', must_exist=True).read_text()
    candidates = [('AGENTS.md', '开发入口本身')]
    candidates += [(link.split('#')[0], label) for label, link in re.findall(r'\[([^\]]+)\]\(([^)]+)\)', agents) if '://' not in link]
    candidates += [(token.rstrip('/'), '') for token in re.findall(r'`([^`\n]+)`', agents) if not any(c in token for c in ' <>*') and ('/' in token or token.endswith(('.md','.yaml')))]
    candidates += [(token.rstrip('/'), '') for token in re.findall(r'\b(?:tools|apps|services|progress|execution|acceptance-runs|contracts|configs|database|install|skills|quality)/[A-Za-z0-9_./-]*', agents)]
    # Unqualified filenames in AGENTS refer to the existing progress ledger.
    candidates += [('progress/current.md', '自动摘要'), ('progress/handoffs','跨会话交接'), ('execution/task-index.yaml','原 32 项任务定义')]
    seen = set(); result = []
    for path,label in candidates:
        if path in seen: continue
        seen.add(path)
        try:
            p = safe_path(root,path,must_exist=True)
        except (ValueError,OSError): continue
        desc,source = describe(path,p.is_dir(),guide)
        result.append({'path':path,'label':label or p.name,'description':desc,'description_source':source,'is_dir':p.is_dir(),'readable':readable(root,path),'expandable':browsable(root,path)})
    return result


