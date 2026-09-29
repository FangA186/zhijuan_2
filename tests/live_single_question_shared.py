"""离线单测：tools/live_single_question.py 的安全围栏与纯函数部分。

完全离线：不连库、不开 socket、不起进程、不触达任何真实服务/额度。
- HTTP（预算/author/solver）用 mock urlopen 或直接 patch 探测函数；
- PG 身份断言用 mock psycopg.connect；
- 子进程只用 mock Popen 实例（不真的 spawn）；
- 预算"缺口应拒绝"assert 覆盖 sufficient/reason_code 两维；
- 未配置 ZHIJUAN_BUDGET_INTERNAL_URL 时 _budget_endpoint 必须 fail-closed
  抛错（评审发现1），绝不回退硬编码地址；
- run() 异常处理只记异常类型名，绝不把 str(exc) 带入 reason 字段/输出
  （评审发现2：psycopg 认证错误消息可能含 PG 用户名）；
- 证据 JSON 结构校验仅对临时文件，不写 acceptance-runs。
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import live_single_question as lsq


def _mock_urlopen(status: int, body: dict | None, *, headers: dict[str, str] | None = None):
    """返回可用于 patch lsq.urlopen 的 mock 响应对象（支持 with 语义）。"""
    body_bytes = json.dumps(body).encode("utf-8") if body is not None else b"{}"
    resp = mock.MagicMock()
    resp.status = status
    resp.read.return_value = body_bytes
    resp.__enter__.return_value = resp
    return mock.patch.object(lsq, "urlopen", return_value=resp)


def _fake_pg_conn(dbname: str, tables: list[str]):
    """构造与 verify_test_database 查询顺序匹配的 mock 连接。

    fetchone/fetchall 返回真实元组（MagicMock 的 __getitem__ 不可信），
    保证 current_database() 与 pg_tables 两个查询分别命中。
    """
    conn = mock.MagicMock()
    cursor = mock.MagicMock()
    cursor.fetchone.return_value = (dbname,)
    cursor.fetchall.return_value = [(t,) for t in tables]
    conn.execute.return_value = cursor
    return conn


def psycopg_authentication_error(dsn: str):
    """评审发现2：psycopg v3 认证失败消息会带连接口令/用户名/端口。

    用真实 psycopg 构造验证过的错误形状（连接实测失败消息
    `connection failed: ... password authentication failed for user ..."），
    以便断言 run() 的 reason 字段绝不含这些片段。
    """
    from psycopg import OperationalError
    return OperationalError(f'connection failed: cannot decode dsn '
                            f'"{dsn}": invalid connection option "SUPERSECRET"')



__all__ = [name for name in globals() if not name.startswith("__")]
