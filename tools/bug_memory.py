#!/usr/bin/env python3
"""Search before fixing; validate and export durable Bug records afterwards."""
import argparse
import json
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.bug_records import load_bugs
from tools.bug_workflow import lookup
from tools.bug_notion import export_pages, mark_synced
from tools.memory_base import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search", help="按症状/路径关键词检索，指定任务时保存修前检索记录")
    search.add_argument("--query", required=True)
    search.add_argument("--task")
    commands.add_parser("check", help="校验全部 Bug 记录")
    commands.add_parser("notion-export", help="导出待同步 payload；本命令不联网")
    synced = commands.add_parser("mark-synced", help="仅在 MCP 写入并回读成功后登记")
    synced.add_argument("--bug", required=True)
    synced.add_argument("--url", required=True)
    synced.add_argument("--hash", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == "search":
            result = lookup(root, args.query, args.task)
        elif args.command == "check":
            result = {"status": "PASS", "bugs": len(load_bugs(root, check_evidence=True))}
        elif args.command == "notion-export":
            result = export_pages(root)
        else:
            mark_synced(root, args.bug, args.url, args.hash)
            result = {"status": "RECORDED", "bug_id": args.bug}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
