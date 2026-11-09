"""Kleine, strikte parser voor het Prometheus-tekstformaat (versie 0.0.4), genoeg voor ``/metrics`` van Uptime Kuma.

Alleen regels ``naam{label="waarde",…} getal [tijd]``; commentaar en ``# HELP``/``# TYPE`` worden overgeslagen.
Labelwaarden ondersteunen de escapes ``\\\\``, ``\\"`` en ``\\n``. Onleesbare regels worden geteld, nooit geraden.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

_NAME = re.compile(r"[a-zA-Z_:][a-zA-Z0-9_:]*")
_LABEL_NAME = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
MAX_LINES = 50_000


@dataclass
class Metric:
    naam: str
    labels: dict[str, str]
    waarde: float


@dataclass
class ParseResult:
    metrics: list[Metric] = field(default_factory=list)
    onleesbaar: int = 0

    def by_name(self, naam: str) -> list[Metric]:
        return [m for m in self.metrics if m.naam == naam]


def _labels(text: str, pos: int) -> tuple[dict[str, str], int]:
    labels: dict[str, str] = {}
    while True:
        while pos < len(text) and text[pos] in " ,":
            pos += 1
        if pos < len(text) and text[pos] == "}":
            return labels, pos + 1
        m = _LABEL_NAME.match(text, pos)
        if not m:
            raise ValueError("labelnaam")
        name = m.group(0)
        pos = m.end()
        if text[pos : pos + 2] != '="':
            raise ValueError("labelwaarde")
        pos += 2
        out: list[str] = []
        while True:
            if pos >= len(text):
                raise ValueError("labelwaarde niet afgesloten")
            ch = text[pos]
            if ch == "\\" and pos + 1 < len(text):
                nxt = text[pos + 1]
                out.append({"n": "\n", "\\": "\\", '"': '"'}.get(nxt, nxt))
                pos += 2
                continue
            if ch == '"':
                pos += 1
                break
            out.append(ch)
            pos += 1
        labels[name] = "".join(out)


def parse(text: str) -> ParseResult:
    res = ParseResult()
    for i, raw in enumerate(text.splitlines()):
        if i >= MAX_LINES:
            res.onleesbaar += 1
            break
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _NAME.match(line)
        if not m:
            res.onleesbaar += 1
            continue
        name, pos = m.group(0), m.end()
        try:
            labels: dict[str, str] = {}
            if pos < len(line) and line[pos] == "{":
                labels, pos = _labels(line, pos + 1)
            parts = line[pos:].split()
            if not parts:
                raise ValueError("geen waarde")
            value = float(parts[0])
        except ValueError:
            res.onleesbaar += 1
            continue
        if math.isnan(value):
            continue
        res.metrics.append(Metric(name, labels, value))
    return res
