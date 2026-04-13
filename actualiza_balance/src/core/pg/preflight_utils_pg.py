# preflight_utils_pg.py — versión PostgreSQL de preflight_utils.py
"""
preflight_utils no contiene SQL ni conexiones de BD.
Este módulo re-exporta todo desde el original para mantener
la consistencia de importaciones en los módulos _pg.py.
"""
from actualiza_balance.src.core.preflight_utils import (
    PreflightItem,
    PreflightResult,
    repo_root,
    ensure_dir,
    make_result,
)

__all__ = [
    "PreflightItem",
    "PreflightResult",
    "repo_root",
    "ensure_dir",
    "make_result",
]
