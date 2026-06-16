"""Subsystem health probes used by ``GET /healthz``.

Each probe returns ``("ok", None)`` on success or ``("fail", "<reason>")`` on
failure — no exceptions escape so /healthz never 500s, only 503s with a
structured body.

Probes are intentionally cheap (a single round-trip each) so the endpoint
can be scraped frequently by load balancers without hurting throughput.
"""

from __future__ import annotations

import asyncio
import socket
from typing import Any

import asyncpg
from redis.asyncio import Redis

from src.config import settings
from src.invites.og_landing import _superuser_dsn
from src.uploads import s3 as s3_mod

ProbeResult = tuple[str, str | None]


async def probe_db() -> ProbeResult:
    try:
        conn = await asyncpg.connect(_superuser_dsn())
        try:
            value = await conn.fetchval("SELECT 1")
            return ("ok", None) if value == 1 else ("fail", "unexpected SELECT 1 result")
        finally:
            await conn.close()
    except Exception as e:
        return "fail", _short(e)


async def probe_redis() -> ProbeResult:
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        pong = await client.ping()
        return ("ok", None) if pong else ("fail", "no PONG")
    except Exception as e:
        return "fail", _short(e)
    finally:
        await client.aclose()


async def probe_s3() -> ProbeResult:
    """``head_bucket`` is the cheapest call we have."""
    try:
        # boto3 is sync — push it to a thread.
        await asyncio.to_thread(
            s3_mod._client(public=False).head_bucket, Bucket=settings.s3_bucket
        )
        return ("ok", None)
    except Exception as e:
        return "fail", _short(e)


async def probe_smtp() -> ProbeResult:
    """A TCP connect is enough — SMTP banner exchange would slow /healthz and
    we already have the SMTP_FROM identity decided at startup."""
    try:
        await asyncio.wait_for(_tcp_check(settings.smtp_host, settings.smtp_port), 2.0)
        return ("ok", None)
    except Exception as e:
        return "fail", _short(e)


async def _tcp_check(host: str, port: int) -> None:
    loop = asyncio.get_running_loop()
    # AF_UNSPEC = IPv4 or IPv6.
    infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not infos:
        raise RuntimeError(f"no addrs for {host}:{port}")
    family, socktype, proto, _, addr = infos[0]
    sock = socket.socket(family, socktype, proto)
    sock.setblocking(False)
    try:
        await loop.sock_connect(sock, addr)
    finally:
        sock.close()


def _short(e: Exception) -> str:
    msg = str(e) or e.__class__.__name__
    return msg.split("\n", 1)[0][:200]


async def collect() -> dict[str, Any]:
    """Run all four probes concurrently; return shape suited for /healthz."""
    db, redis, s3, smtp = await asyncio.gather(
        probe_db(), probe_redis(), probe_s3(), probe_smtp()
    )
    checks = {
        "db": _to_dict(db),
        "redis": _to_dict(redis),
        "s3": _to_dict(s3),
        "smtp": _to_dict(smtp),
    }
    ok = all(c["status"] == "ok" for c in checks.values())
    return {"status": "ok" if ok else "degraded", "checks": checks}


def _to_dict(probe: ProbeResult) -> dict[str, str | None]:
    status, error = probe
    return {"status": status, "error": error}
