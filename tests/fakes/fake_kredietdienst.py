"""Lokale kredietdienst met een vast tegoed en een teller voor werkelijk ontvangen verzoeken."""

from __future__ import annotations

import json

from fakes.fake_http import FakeHTTP, Reply, Seen


class FakeKredietdienst(FakeHTTP):
    def __init__(self, eenheden: int) -> None:
        super().__init__()
        self.eenheden = eenheden
        self.advies = {"analyse": "Controleer de bronmeting."}

    def handle(self, seen: Seen) -> Reply:
        if (seen.method, seen.path) != ("POST", "/diagnose"):
            return Reply(404)
        taak = json.loads(seen.body)
        kosten = taak["max_eenheden"]
        if taak["alleen_inbegrepen"] is not True or type(kosten) is not int or kosten <= 0:
            return Reply(422)
        if kosten > self.eenheden:
            return Reply(402)
        self.eenheden -= kosten
        return Reply(200, self.advies)
