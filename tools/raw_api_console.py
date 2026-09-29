"""User-run setup: configure the provider tap; the existing API serves captured responses."""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.local_runtime import load_dotenv
from tools.local_runtime_generation import _active_jobs
from tools.raw_api_server import DEFAULT_DIR

PROJECT = 'zhijuan-workflow-20260922-live'


def configure_capture(enabled, thinking):
    load_dotenv()
    active, error = _active_jobs()
    if error or active:
        raise RuntimeError('生成任务仍在运行或状态不可读；待任务结束后再重载代理。')
    env = dict(os.environ)
    sources = [
        ('budget-proxy', ['DEEPSEEK_UPSTREAM_API_KEY', 'ZHIJUAN_BUDGET_PROXY_TOKEN']),
        ('solver-entry', ['HERMES_SOLVER_UPSTREAM_KEY']),
    ]
    for service, keys in sources:
        # Existing credential values stay only in subprocess memory/environment, never printed or saved.
        result = subprocess.run(['docker', 'inspect', '--format', '{{json .Config.Env}}', f'{PROJECT}-{service}-1'],
                                check=True, capture_output=True, text=True)
        retained = dict(entry.split('=', 1) for entry in json.loads(result.stdout) if '=' in entry)
        for key in keys:
            if not retained.get(key):
                raise RuntimeError('现有容器配置不完整：' + key)
            env[key] = retained[key]
    DEFAULT_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    env['ZHIJUAN_RAW_API_DIR'] = '/raw-api' if enabled else ''
    env['ZHIJUAN_DIAGNOSTIC_THINKING'] = thinking if enabled else 'disabled'
    command = ['docker', 'compose', '-p', PROJECT, '-f', 'infra/workflow-acceptance/compose.yaml',
               '-f', 'infra/workflow-acceptance/compose.local-override.yaml', 'up', '-d', '--no-deps', 'budget-proxy']
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('预算代理重载失败；原始配置输出不写入终端，请检查本机Docker。')
    receipt = {'capture_enabled': enabled, 'thinking_mode': thinking if enabled else 'disabled',
               'configured_at': datetime.now(timezone.utc).isoformat()}
    (DEFAULT_DIR / 'settings.json').write_text(json.dumps(receipt))
    print('Viewer: http://localhost:3000/raw-api.html (existing API port 8000)', flush=True)
    print(f'Capture={enabled}; thinking={env["ZHIJUAN_DIAGNOSTIC_THINKING"]}; no generation was started.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['start', 'stop'])
    parser.add_argument('--thinking', choices=['enabled', 'disabled'], default='enabled')
    args = parser.parse_args()
    configure_capture(args.command == 'start', args.thinking)
