"""Narrow RabbitMQ controls used by the local generation commands."""
from __future__ import annotations

import os
import socket
import subprocess
import time

from tools.local_runtime_config import BROKER_HOST, BROKER_PORT, MQ_CONTAINER, VHOST

def _broker_user() -> str:
    """从 CELERY_BROKER_URL 提取非秘密的 AMQP 用户名（绝不取出/输出密码）。"""
    url = os.getenv("CELERY_BROKER_URL", "")
    if url.startswith(("amqp://", "amqps://")):
        authority = url.split("://", 1)[1].split("/", 1)[0]
        if "@" in authority:
            user = authority.split("@", 1)[0].split(":", 1)[0]
            if user:
                return user
    return "guest"


def docker_exec_mq(ctl_args: list[str], timeout: float = 30.0) -> tuple[int, str, str]:
    """仅允许对该 mq 容器执行 rabbitmqctl add_vhost / set_permissions。"""
    if len(ctl_args) < 2 or ctl_args[0] != "rabbitmqctl":
        raise RuntimeError("docker exec 仅允许 rabbitmqctl")
    if ctl_args[1] not in ("add_vhost", "set_permissions"):
        raise RuntimeError("仅允许 rabbitmqctl add_vhost / set_permissions")
    proc = subprocess.run(
        ["docker", "exec", MQ_CONTAINER] + ctl_args,
        capture_output=True, text=True, timeout=timeout,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def ensure_vhost(*, broker_user_fn=_broker_user, docker_exec_mq_fn=docker_exec_mq) -> tuple[bool, str]:
    """确保 vhost zhijuan-local 存在并允许当前用户读写 generation 队列。

    add_vhost 已存在视为成功（幂等）；任何失败都转为手动步骤提示。
    """
    user = broker_user_fn()
    rc, out, err = docker_exec_mq_fn(["rabbitmqctl", "add_vhost", VHOST])
    if rc != 0 and "already exists" not in (err + out).lower() and "exists" not in (err + out).lower():
        manual = (
            f"docker exec {MQ_CONTAINER} rabbitmqctl add_vhost {VHOST}\n"
            f"             docker exec {MQ_CONTAINER} rabbitmqctl set_permissions -p {VHOST} {user} \".*\" \".*\" \".*\""
        )
        return False, f"vhost 准备失败（请手动执行）:\n{manual}\n  实际错误: {err or out or rc}"
    rc, out, err = docker_exec_mq_fn(
        ["rabbitmqctl", "set_permissions", "-p", VHOST, user,
         ".*", ".*", ".*"])
    if rc != 0:
        manual = (f"docker exec {MQ_CONTAINER} rabbitmqctl set_permissions "
                  f"-p {VHOST} {user} \".*\" \".*\" \".*\"")
        return False, f"set_permissions 失败（请手动执行）:\n{manual}\n  实际错误: {err or rc}"
    return True, f"vhost {VHOST} 就绪（user={user}，最小权限）"


def _wait_amqp_ready(timeout: float = 30.0, interval: float = 1.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            sock = socket.create_connection((BROKER_HOST, BROKER_PORT), timeout=2.0)
            sock.sendall(b"AMQP\x00\x00\x09\x01")
            reply = sock.recv(16)
            sock.close()
            # 回显协议头或 connection.start 方法帧（RabbitMQ 4）都算就绪。
            if reply.startswith(b"AMQP") or (
                    len(reply) >= 9 and reply[0] == 0x01 and reply[7:9] == b"\x00\x0a"):
                return True
        except OSError:
            pass
        time.sleep(interval)
    return False
