"""Fakes voor monitoringbronnen (alleen tests), gemodelleerd naar de broncode die de Hub-adapters noemen:

- ``FakeUptimeKuma`` (Uptime Kuma 2.5.9): ``/metrics`` achter HTTP Basic met API-key als wachtwoord
  (``monitor_status`` 1/0/2/3, ``monitor_response_time``, ``monitor_uptime_ratio{window}``, ``app_version``) en de
  status-page-API (``/api/status-page/{slug}``, ``/api/status-page/heartbeat/{slug}``).
- ``FakeBeszel`` (Beszel 0.21.1 / PocketBase): ``auth-with-password``, ``/api/beszel/info``, ``systems`` en
  ``system_stats`` (filter op ``system`` en ``type='1m'``).
- ``FakeDienst``: een eigen dienst met ``GET /connector/v1/health`` die de dienst-JWT van de Hub echt controleert.
Allemaal met storingsinjectie via ``FakeHTTP`` (offline, geforceerde status, vertraging, redirect).
"""

from __future__ import annotations

import base64
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from fakes.fake_http import FakeHTTP, Reply, Seen

GIB = 1024**3


def _esc(v: str) -> str:
    return v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def kuma_time(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S.") + f"{dt.microsecond // 1000:03d}"


class FakeUptimeKuma(FakeHTTP):
    def __init__(self, api_keys: set[str] | None = None, version: str = "2.5.9", with_ids: bool = True) -> None:
        super().__init__()
        self.api_keys = api_keys if api_keys is not None else {"uk1_testkey_abcdef"}
        self.version = version
        self.with_ids = with_ids
        self.monitors: list[dict[str, Any]] = []
        self.status_pages: dict[str, list[int]] = {}

    def add(self, mid: int, name: str, *, url: str | None = None, status: int = 1, ping: float = 12.0,
            hostname: str | None = None, port: int | None = None, mtype: str = "http") -> None:  # fmt: skip
        self.monitors.append(
            {
                "id": mid,
                "name": name,
                "type": mtype,
                "url": url,
                "hostname": hostname,
                "port": port,
                "status": status,
                "ping": ping,
                "uptime": 0.99,
                "time": datetime.now(UTC),
            }
        )

    def _labels(self, m: dict[str, Any]) -> str:
        parts = []
        if self.with_ids:
            parts.append(f'monitor_id="{m["id"]}"')
        parts += [
            f'monitor_name="{_esc(m["name"])}"',
            f'monitor_type="{m["type"]}"',
            f'monitor_url="{_esc(m["url"] or "null")}"',
            f'monitor_hostname="{m["hostname"] or "null"}"',
            f'monitor_port="{m["port"] or "null"}"',
        ]
        return ",".join(parts)

    def metrics_text(self) -> str:
        v = self.version.split(".")
        lines = [
            "# HELP app_version The service version by package.json",
            "# TYPE app_version gauge",
            f'app_version{{version="{self.version}",major="{v[0]}",minor="{v[1]}",patch="{v[2]}"}} 1',
            "# HELP monitor_status Monitor Status (1 = UP, 0= DOWN, 2= PENDING, 3= MAINTENANCE)",
            "# TYPE monitor_status gauge",
        ]
        for m in self.monitors:
            lab = self._labels(m)
            lines.append(f"monitor_status{{{lab}}} {m['status']}")
            lines.append(f"monitor_response_time{{{lab}}} {m['ping']}")
            lines.append(f'monitor_uptime_ratio{{{lab},window="1d"}} {m["uptime"]}')
        lines.append("process_cpu_seconds_total 1.5")
        return "\n".join(lines) + "\n"

    def handle(self, seen: Seen) -> Reply:
        if seen.path == "/metrics":
            auth = seen.headers.get("authorization", "")
            ok = False
            if auth.startswith("Basic "):
                try:
                    _user, _sep, pw = base64.b64decode(auth[6:]).decode().partition(":")
                    ok = pw in self.api_keys
                except ValueError:
                    ok = False
            if not ok:
                return Reply(401, "Unauthorized", {"WWW-Authenticate": 'Basic realm="Uptime Kuma"'})
            return Reply(200, self.metrics_text())
        m = re.fullmatch(r"/api/status-page/heartbeat/([a-z0-9-]+)", seen.path)
        if m:
            ids = self.status_pages.get(m.group(1))
            if ids is None:
                return Reply(404, {"ok": False, "msg": "Status Page Not Found"})
            beats, up = {}, {}
            for mon in self.monitors:
                if mon["id"] in ids:
                    t = mon["time"]
                    beats[str(mon["id"])] = [
                        {"status": 1, "time": kuma_time(t - timedelta(minutes=1)), "msg": "", "ping": mon["ping"]},
                        {"status": mon["status"], "time": kuma_time(t), "msg": "", "ping": mon["ping"]},
                    ]
                    up[f"{mon['id']}_24"] = mon["uptime"]
            return Reply(200, {"heartbeatList": beats, "uptimeList": up})
        m = re.fullmatch(r"/api/status-page/([a-z0-9-]+)", seen.path)
        if m:
            ids = self.status_pages.get(m.group(1))
            if ids is None:
                return Reply(404, {"ok": False, "msg": "Status Page Not Found"})
            mons = [
                {"id": x["id"], "name": x["name"], "sendUrl": 0, "type": x["type"]}
                for x in self.monitors
                if x["id"] in ids
            ]
            return Reply(
                200,
                {
                    "config": {"slug": m.group(1), "title": "Status"},
                    "incidents": [],
                    "publicGroupList": [{"id": 1, "name": "Diensten", "weight": 1, "monitorList": mons}],
                    "maintenanceList": [],
                },
            )
        return Reply(404, "Not Found")


def pb_time(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def nas_stats(gpus: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "cpu": 12.5,
        "m": 32.0,
        "mu": 8.0,
        "mp": 25.0,
        "mem": [32 * GIB, 8 * GIB, 4 * GIB, 6 * GIB],
        "dio": [1000, 2000],
        "b": [300, 400],
        "t": {"coretemp_package_id_0": 48.0, "nvme_composite": 40.0, "acpitz": 0.0},
        "g": gpus
        if gpus is not None
        else {
            "card0": {"n": "Intel Arc A310", "u": 30.0, "p": 9.5},
            "card1": {"n": "Intel UHD Graphics 770", "u": 5.0},
        },
    }


class FakeBeszel(FakeHTTP):
    def __init__(self, users: dict[str, str] | None = None, version: str = "0.21.1") -> None:
        super().__init__()
        self.users = users if users is not None else {"hub-lezer": "Lees-Alleen-Wachtwoord-1"}
        self.version = version
        self.tokens: set[str] = set()
        self.systems: list[dict[str, Any]] = [
            {"id": "nas000000000001", "name": "truenas", "host": "127.0.0.1", "port": "45876", "status": "up"},
            {"id": "mini00000000001", "name": "mini-pc", "host": "192.0.2.50", "port": "45876", "status": "up"},
        ]
        now = datetime.now(UTC)
        self.stats: dict[str, dict[str, Any]] = {
            "nas000000000001": {"stats": nas_stats(), "created": now - timedelta(seconds=20)},
            "mini00000000001": {"stats": {**nas_stats({}), "cpu": 99.0}, "created": now - timedelta(seconds=20)},
        }

    def _authed(self, seen: Seen) -> bool:
        return seen.headers.get("authorization", "") in self.tokens

    def handle(self, seen: Seen) -> Reply:
        if seen.path == "/api/collections/users/auth-with-password" and seen.method == "POST":
            body = json.loads(seen.body or b"{}")
            if self.users.get(str(body.get("identity"))) != body.get("password"):
                return Reply(400, {"code": 400, "message": "Failed to authenticate.", "data": {}})
            tok = f"pbtok.{len(self.tokens) + 1}.x"
            self.tokens.add(tok)
            return Reply(200, {"token": tok, "record": {"id": "u1", "role": "readonly"}})
        if not self._authed(seen):
            return Reply(
                401, {"code": 401, "message": "The request requires valid record authorization token.", "data": {}}
            )
        if seen.path == "/api/beszel/info":
            return Reply(200, {"key": "ssh-ed25519 AAAATEST", "v": self.version, "cu": False})
        if seen.path == "/api/collections/systems/records":
            items = [
                {**s, "info": {"v": self.version, "cpu": 1.0}, "updated": pb_time(datetime.now(UTC))}
                for s in self.systems
            ]
            return Reply(200, {"page": 1, "perPage": 200, "totalItems": len(items), "totalPages": 1, "items": items})
        if seen.path == "/api/collections/system_stats/records":
            flt = (seen.query.get("filter") or [""])[0]
            m = re.fullmatch(r"\(system='([a-z0-9]+)' && type='1m'\)", flt)
            if not m:
                return Reply(400, {"code": 400, "message": "Invalid filter.", "data": {}})
            rec = self.stats.get(m.group(1))
            items = (
                []
                if rec is None
                else [
                    {
                        "id": "st1",
                        "system": m.group(1),
                        "type": "1m",
                        "stats": rec["stats"],
                        "created": pb_time(rec["created"]),
                    }
                ]
            )
            return Reply(200, {"page": 1, "perPage": 1, "totalItems": len(items), "totalPages": 1, "items": items})
        return Reply(404, {"code": 404, "message": "Not found.", "data": {}})


class FakeDienst(FakeHTTP):
    """Eigen dienst met ``GET /connector/v1/health`` (contract §6) die de dienst-JWT van de Hub controleert."""

    def __init__(self, public_key: Any, app_id: str, service_id: str | None = None) -> None:
        super().__init__()
        self.public_key, self.app_id, self.service_id = public_key, app_id, service_id
        self.health: dict[str, Any] = {"status": "healthy", "reason_code": None, "checks": []}
        self.rejected: list[str] = []

    def handle(self, seen: Seen) -> Reply:
        if seen.path != "/connector/v1/health":
            return Reply(404, {"code": "not_found", "message": "Niet gevonden.", "details": {}, "trace_id": "x"})
        auth = seen.headers.get("authorization", "")
        try:
            claims = jwt.decode(
                auth.removeprefix("Bearer "), self.public_key, algorithms=["EdDSA"], audience=self.app_id
            )
        except jwt.PyJWTError as exc:
            self.rejected.append(type(exc).__name__)
            return Reply(401, {"code": "unauthorized", "message": "Nee.", "details": {"reason": "invalid_token"}})
        if claims.get("token_use") != "hub_service" or (
            self.service_id and claims.get("service_id") != self.service_id
        ):
            self.rejected.append("token_use")
            return Reply(401, {"code": "unauthorized", "message": "Nee.", "details": {"reason": "token_use_invalid"}})
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        body = {**self.health, "observed_at": now}
        body["checks"] = [{**c, "observed_at": now} for c in self.health.get("checks", [])]
        return Reply(200, body)
