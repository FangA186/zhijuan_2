import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from services.api.main import app
from services.api.routes import raw_api_routes as routes


class RawRouteTests(unittest.TestCase):
    def test_remote_and_cross_site_requests_are_rejected(self):
        self.assertEqual(TestClient(app, client=('203.0.113.8',1)).get('/v1/raw-api/status').status_code,403)
        self.assertEqual(TestClient(app).post('/v1/raw-api/clear',headers={'Origin':'https://example.org'}).status_code,403)

    def test_clear_archives_and_status_distinguishes_actual_proxy_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'responses.ndjson'
            path.write_text('{"raw":"test"}\n')
            with patch.object(routes,'_capture_path',return_value=path), patch.object(routes,'_DEFAULT_DIR',Path(directory)):
                client=TestClient(app)
                self.assertIsNone(client.get('/v1/raw-api/status').json()['capture_enabled'])
                archived=client.post('/v1/raw-api/clear').json()['archive']
                self.assertFalse(path.exists())
                self.assertEqual((Path(directory)/archived).read_text(),'{"raw":"test"}\n')
                (Path(directory)/'settings.json').write_text(json.dumps({'capture_enabled':True,'thinking_mode':'enabled'}))
                self.assertEqual(client.get('/v1/raw-api/status').json()['thinking_mode'],'enabled')

    def test_sse_resume_uses_last_event_id(self):
        async def check():
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'responses.ndjson'
                first=b'{"raw":"one"}\n'
                path.write_bytes(first+b'{"raw":"two"}\n')
                with patch.object(routes,'_capture_path',return_value=path):
                    response=await routes.raw_api_events(0,str(len(first)))
                    data=await anext(response.body_iterator)
                    self.assertIn('two',data)
                    self.assertNotIn('one',data)
                    await response.body_iterator.aclose()
        asyncio.run(check())
