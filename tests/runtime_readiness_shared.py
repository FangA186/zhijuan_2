"""Offline tests for real runtime readiness (W2-B).

All probes are mocked or bound to a throwaway 127.0.0.1 HTTP server that is
closed after each test. Nothing here hits a real database, broker, model
provider, budget proxy or vendor gateway.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import types
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import psycopg

from services import api
from services.api import health
from services.api.settings import settings
from services.api.main import app
from services.hermes_adapter.isolation_gateway import Handler as GatewayHandler
from fastapi.testclient import TestClient


CONFIGURED = {'configured': True, 'checks': {'database': True, 'queue': True, 'author': True, 'isolated_solver': True},
              'runtime_verified': False}

# A fully-configured environment so the real generation_configuration() is
# True without mocking; keeps the readiness cache signature distinct from the
# cleared-env state used by other modules' tests.
CONFIGURED_ENV = {
    'DATABASE_URL': 'fixture-db',
    'CELERY_BROKER_URL': 'amqp://fixture',
    'HERMES_API_BASE_URL': 'http://author.test',
    'HERMES_API_KEY': 'author-key-fixture',
    'HERMES_SOLVER_API_BASE_URL': 'http://solver.test',
    'HERMES_SOLVER_API_KEY': 'solver-key-fixture',
    'HERMES_SOLVER_MODEL_ID': 'deepseek-flash',
    'ZHIJUAN_DEEPSEEK_MODEL_ID': 'deepseek-flash',
}


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, json_raises=None):
        self.status_code = status_code
        self._json = json_data
        self._json_raises = json_raises
        self.headers = {}

    def json(self):
        if self._json_raises is not None:
            raise self._json_raises
        return self._json


class FakeHttpxClient:
    """Context-manager stand-in for httpx.Client that returns canned responses."""
    def __init__(self, response, **kwargs):
        self._response = response
        self.last_request = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, **kwargs):
        self.last_request = (url, kwargs)
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


class FakeCursor:
    def __init__(self, rows):
        self._rows = list(rows) if not isinstance(rows, list) else rows
        self.rows_iter = iter(self._rows)

    def fetchone(self):
        try:
            return next(self.rows_iter)
        except StopIteration:
            return None

    def __iter__(self):
        return iter(self._rows)


class FakeConn:
    def __init__(self, execute=None):
        self.execute = execute or MagicMock(return_value=FakeCursor([]))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def ok_probe(name):
    return lambda timeout: {"ok": True}


def ok_heartbeats(timeout):
    return {"worker": {"ok": True}, "dispatcher": {"ok": True}}


PROBE_REASON = {
    '_probe_database': 'DATABASE_UNAVAILABLE', '_probe_broker': 'BROKER_UNAVAILABLE',
    '_probe_author': 'AUTHOR_UNAVAILABLE', '_probe_solver': 'SOLVER_UNAVAILABLE',
    '_probe_budget': 'BUDGET_UNAVAILABLE', '_probe_heartbeats': 'WORKER_UNAVAILABLE',
}


def fail_probe(name):
    return lambda timeout: {"ok": False, "reason": PROBE_REASON.get(name, name)}



__all__ = [name for name in globals() if not name.startswith("__")]
