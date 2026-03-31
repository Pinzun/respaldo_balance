# scripts/preflight_utils.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List
import os


@dataclass
class PreflightItem:
    label: str
    path: Path
    must_exist: bool = True


@dataclass
class PreflightResult:
    module: str
    items: List[PreflightItem]
    missing: List[PreflightItem] = field(default_factory=list)
    mode: str = "strict"  # "strict" o "skip"

    # --- status derivado (sin setters externos) ---
    @property
    def ok(self) -> bool:
        return len(self.missing) == 0

    @property
    def skip(self) -> bool:
        # En skip-mode, si faltan requeridos => se omite
        return (self.mode == "skip") and (not self.ok)

    @property
    def fail(self) -> bool:
        # En strict-mode, si faltan requeridos => falla
        return (self.mode != "skip") and (not self.ok)

    def print_report(self) -> None:
        # Header con estado
        if self.ok:
            header = "✅ OK"
            hint = ""
        elif self.skip:
            header = "⏭️ SKIP"
            hint = "  ↳ No hay insumos requeridos (archivos/carpetas). Se omite el módulo en esta corrida."
        else:
            header = "❌ FAIL"
            hint = "  ↳ Faltan insumos requeridos."

        print(f"\n🧪 PREFLIGHT :: {self.module} :: {header}")
        if hint:
            print(hint)

        for it in self.items:
            exists = it.path.exists()
            status = "✅" if exists else ("⚠️" if not it.must_exist else "❌")
            req = "REQ" if it.must_exist else "OPT"
            print(f"  {status} [{req}] {it.label}: {it.path}")

        if self.missing:
            print(f"  ❌ Faltan {len(self.missing)} requeridos:")
            for it in self.missing:
                print(f"     - {it.label}: {it.path}")


def repo_root() -> Path:
    # scripts/ -> repo_root/
    return Path(__file__).resolve().parent.parent


def ensure_dir(path: Path) -> None:
    os.makedirs(path, exist_ok=True)


def make_result(module: str, items: Iterable[PreflightItem], mode: str = "strict") -> PreflightResult:
    items = list(items)
    missing = [it for it in items if it.must_exist and not it.path.exists()]
    return PreflightResult(module=module, items=items, missing=missing, mode=mode)