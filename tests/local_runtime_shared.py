"""Offline unit tests for tools/local_runtime.py.

These tests never call docker, never open real network sockets, and never
spawn real processes: subprocess.Popen / subprocess.run are mocked, socket
and urlopen are mocked, and the PG heartbeat reader is mocked at the
services.api.runtime_heartbeats module level.
"""
from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from tools import local_runtime as lr



__all__ = [name for name in globals() if not name.startswith("__")]
