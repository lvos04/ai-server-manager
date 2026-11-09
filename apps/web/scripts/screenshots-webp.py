"""Schermafdrukken van de web-E2E (JPEG, Playwright) omzetten naar WebP voor in Git (kleiner, zelfde inhoud).

Gebruik (lokaal, na `npx playwright test`): python3 scripts/screenshots-webp.py ../../docs/screenshots/p1
Vereist Pillow (alleen voor deze stap; geen afhankelijkheid van de app of van CI).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


def main(root: Path) -> int:
    n = before = after = 0
    for jpg in sorted(root.rglob("*.jpg")):
        webp = jpg.with_suffix(".webp")
        with Image.open(jpg) as im:
            im.save(webp, "WEBP", quality=60, method=6)
        before += jpg.stat().st_size
        after += webp.stat().st_size
        jpg.unlink()
        n += 1
    print(f"{n} afdrukken omgezet: {before // 1024} KiB → {after // 1024} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "../../docs/screenshots/p1")))
