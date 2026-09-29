"""Local HTTP server and JSON/image routes for the vocabulary viewer."""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

if __package__:
    from .vocab_detector import detect_vocab_in_book
    from .vocab_viewer_template import HTML_TEMPLATE
    from .vocab_viewer_catalog import build_catalog_tree
    from .vocab_viewer_operations import delete_files, restore_trash_files
    from .vocab_viewer_paths import TRASH_DIR, get_safe_path, get_safe_trash_path, list_book_images, list_trash_images
else:
    from vocab_detector import detect_vocab_in_book
    from vocab_viewer_template import HTML_TEMPLATE
    from vocab_viewer_catalog import build_catalog_tree
    from vocab_viewer_operations import delete_files, restore_trash_files
    from vocab_viewer_paths import TRASH_DIR, get_safe_path, get_safe_trash_path, list_book_images, list_trash_images


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True



class VocabViewerHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
            return

        if path == "/api/tree":
            data = build_catalog_tree()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/images":
            rel_path = query.get("path", [""])[0]
            items = list_book_images(rel_path)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(items, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/detect_vocab":
            rel_path = query.get("path", [""])[0]
            force = query.get("force", ["0"])[0] in ("1", "true")
            data = detect_vocab_in_book(rel_path, force_refresh=force)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/trash":
            rel_path = query.get("path", [""])[0]
            items = list_trash_images(rel_path)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(items, ensure_ascii=False).encode("utf-8"))
            return

        if path.startswith("/trash_image/"):
            rel_file_path = urllib.parse.unquote(path[13:])
            try:
                full_path = get_safe_trash_path(rel_file_path)
                if not os.path.exists(full_path):
                    self.send_error(404, "Trash image not found")
                    return

                with open(full_path, "rb") as f:
                    content = f.read()

                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(content)
            except Exception as e:
                self.send_error(403, str(e))
            return

        if path.startswith("/image/"):
            rel_file_path = urllib.parse.unquote(path[7:])
            try:
                full_path = get_safe_path(rel_file_path)
                if not os.path.exists(full_path):
                    self.send_error(404, "Image not found")
                    return

                with open(full_path, "rb") as f:
                    content = f.read()

                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(content)
            except Exception as e:
                self.send_error(403, str(e))
            return

        self.send_error(404, "Not Found")

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/delete":
            content_len = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_len).decode("utf-8"))
            files = body.get("files", [])
            use_trash = body.get("trash", True)

            result = delete_files(files, use_trash=use_trash)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/restore":
            content_len = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_len).decode("utf-8"))
            files = body.get("files", [])
            result = restore_trash_files(files)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            return

        self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        if args and isinstance(args[0], str) and "/image/" in args[0]:
            return
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

