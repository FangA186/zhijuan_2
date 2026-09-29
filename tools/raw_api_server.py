"""Loopback-only response-file SSE reader. GET never calls a model."""
import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / '.runtime/raw-api'


def read_records(path, offset=0):
    if not path.exists():
        return
    with path.open('rb') as stream:
        stream.seek(offset if 0 <= offset <= path.stat().st_size else 0)
        while True:
            line = stream.readline()
            if not line or not line.endswith(b'\n'):
                return
            try:
                record = json.loads(line)
            except ValueError:
                continue
            yield stream.tell(), record


def make_handler(directory):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get('Host', '').split(':')[0] not in {'127.0.0.1', 'localhost'}:
                self.send_error(403)
                return
            origin = self.headers.get('Origin')
            if origin and origin not in {'http://localhost:3000', 'http://127.0.0.1:3000',
                                         f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'}:
                self.send_error(403)
                return
            url = urlparse(self.path)
            if url.path != '/events':
                self.send_error(404)
                return
            try:
                offset = int(self.headers.get('Last-Event-ID') or parse_qs(url.query).get('after', ['0'])[0])
            except ValueError:
                self.send_error(400)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            if origin:
                self.send_header('Access-Control-Allow-Origin', origin)
            self.end_headers()
            try:
                while True:
                    found = False
                    for offset, record in read_records(directory / 'responses.ndjson', offset):
                        frame = f'id: {offset}\ndata: {json.dumps(record, ensure_ascii=False)}\n\n'
                        self.wfile.write(frame.encode())
                        found = True
                    if not found:
                        self.wfile.write(b': waiting for provider response\n\n')
                    self.wfile.flush()
                    time.sleep(.3)
            except (BrokenPipeError, ConnectionResetError):
                return

        def log_message(self, *args):
            pass
    return Handler


def serve(directory=DEFAULT_DIR, port=8768):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    print(f'Raw data reader: http://127.0.0.1:{port}/events', flush=True)
    print('Viewer: http://localhost:3000/raw-api.html', flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), make_handler(directory)).serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8768)
    args = parser.parse_args()
    serve(port=args.port)
