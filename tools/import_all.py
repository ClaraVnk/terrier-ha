"""Import every module of the integration on the Home Assistant installed.

Run by CI on the release hacs.json declares as the minimum. Review of
2026-11-18: hacs.json said 2024.12.0 and every platform imported a name that
first appeared in 2025.3.0; nothing loaded the code on the declared release,
so nothing noticed.

    pip install "homeassistant==<hacs.json's>" && python tools/import_all.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

failed = []
for path in sorted((ROOT / "custom_components" / "terrier").glob("*.py")):
    name = f"custom_components.terrier.{path.stem}".removesuffix(".__init__")
    try:
        importlib.import_module(name)
    except Exception as err:  # every failure, reported at once
        failed.append(f"{name}: {type(err).__name__}: {err}")
    else:
        print(f"ok  {name}")
print("\n".join(failed))
sys.exit(1 if failed else 0)
