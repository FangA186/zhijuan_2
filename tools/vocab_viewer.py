#!/usr/bin/env python3
"""知卷 - 教材单词图片层级审查与清洗管理服务。"""

import argparse
import os
import sys
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __package__:
    from .vocab_viewer_catalog import build_catalog_tree
    from .vocab_viewer_operations import delete_files, restore_trash_files
    from .vocab_viewer_paths import BASE_DIR, TRASH_DIR, get_safe_path, get_safe_trash_path, list_book_images, list_trash_images
    from .vocab_viewer_server import ThreadingHTTPServer, VocabViewerHandler
    from .vocab_viewer_template import HTML_TEMPLATE
else:
    from vocab_viewer_catalog import build_catalog_tree
    from vocab_viewer_operations import delete_files, restore_trash_files
    from vocab_viewer_paths import BASE_DIR, TRASH_DIR, get_safe_path, get_safe_trash_path, list_book_images, list_trash_images
    from vocab_viewer_server import ThreadingHTTPServer, VocabViewerHandler
    from vocab_viewer_template import HTML_TEMPLATE


def main():
    parser = argparse.ArgumentParser(description="知卷 - 单词原图层级审查与清洗管理服务")
    parser.add_argument("--port", type=int, default=8088, help="服务运行端口 (默认: 8088)")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    server_address = ("127.0.0.1", args.port)
    httpd = ThreadingHTTPServer(server_address, VocabViewerHandler)

    url = f"http://127.0.0.1:{args.port}"
    print("=" * 65)
    print(" 📖 知卷 - 英语教材单词原图层级审查与清洗工作台")
    print(f" 服务地址: {url}")
    print(f" 数据主目录: {BASE_DIR}")
    print(f" 回收站目录: {TRASH_DIR}")
    print(" 提示: 默认开启【删除模式】，点击图片任意位置直接勾选，按 Delete 键一键删除！")
    print("=" * 65)

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已平稳停止。")



if __name__ == "__main__":
    main()
