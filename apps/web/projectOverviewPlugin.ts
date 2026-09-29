import { execFile } from 'node:child_process';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { Plugin } from 'vite';

/** Local-only metadata bridge. No app imports, file writes, or model calls. */
export function projectOverviewPlugin(): Plugin {
  const root = fileURLToPath(new URL('../../', import.meta.url));
  const python = resolve(root, '.venv/bin/python');
  return {
    name: 'local-project-overview',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use('/__project', (req, res, next) => {
        const url = new URL(req.url || '/', 'http://localhost');
        const mode = url.pathname.slice(1);
        if (!['snapshot', 'tree', 'document'].includes(mode)) return next();
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.setHeader('Cache-Control', 'no-store');
        const remote = req.socket.remoteAddress;
        const local = ['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(remote || '');
        const localHost = /^(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$/i.test(req.headers.host || '');
        const origin = req.headers.origin;
        const sameOrigin = !origin || origin === `http://${req.headers.host}` || origin === `https://${req.headers.host}`;
        if (req.method !== 'GET' || !local || !localHost || !sameOrigin || req.headers['sec-fetch-site'] === 'cross-site') {
          res.statusCode = 403;
          res.end(JSON.stringify({ error: '项目资料仅允许本机同源只读访问。' }));
          return;
        }
        execFile(existsSync(python) ? python : 'python3', [resolve(root, 'tools/project_overview.py'), mode, '--path', url.searchParams.get('path') || '', '--offset', url.searchParams.get('offset') || '0', '--query', url.searchParams.get('query') || ''], {
          cwd: root, timeout: 30000, maxBuffer: 4 * 1024 * 1024,
          env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
        }, (error, stdout) => {
          if (error) {
            res.statusCode = 400;
            res.end(JSON.stringify({ error: '读取失败：路径受限、记录无效或项目 Python 依赖未就绪。' }));
          } else res.end(stdout);
        });
      });
    },
  };
}
