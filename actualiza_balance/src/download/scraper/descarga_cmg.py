"""
descarga_cmg.py — Descarga de CMG Real por rango de fechas desde coordinador.cl.
"""
from __future__ import annotations

import argparse
from calendar import monthrange
from datetime import date, datetime, timedelta
from pathlib import Path

from ._shared import (
    _BrowserSession,
    _descargar_bloque_coordinador,
    _normalize_coordinador_host,
    log_info,
    log_warn,
)

# ======================================================
# Helpers específicos de CMG
# ======================================================
def _add_months(d: date, delta: int) -> date:
    """
    Suma delta meses a una fecha.
    Mantiene el día si existe; si no, recorta al último día del mes resultante.
    """
    y = d.year
    m = d.month + delta
    y += (m - 1) // 12
    m = ((m - 1) % 12) + 1
    last = monthrange(y, m)[1]
    return date(y, m, min(d.day, last))


def _cmg_url_for_shift(d: date, month_shift: int, base="https://www.coordinador.cl/wp-content/uploads") -> str:
    """Construye URL CMG para el día d, probando carpeta desplazada por month_shift meses."""
    folder = _add_months(d, month_shift)
    ymd_short = d.strftime("%y%m%d")
    url = f"{base}/{folder:%Y/%m}/Antecedentes_CMG_Real_def_{ymd_short}.zip"
    return _normalize_coordinador_host(url)


def resolver_cmg_url_con_browser_por_dia(
    br: "_BrowserSession",
    d: date,
    base="https://www.coordinador.cl/wp-content/uploads",
    max_shift: int = 2,
) -> str:
    """
    Prueba shift+0..shift+max_shift y retorna la primera URL que "existe".
    Existencia: 2xx/3xx => existe; 403 => existe (protegido).
    """
    for k in range(0, max_shift + 1):
        u = _cmg_url_for_shift(d, month_shift=k, base=base)
        carpeta = "/".join(u.split("/")[-3:-1])
        nombre = u.split("/")[-1]
        st = br.probe_status_head(u, timeout=20)
        log_info(f"[resolve+chrome][cmg-day] {d} probando shift+{k} ({carpeta}) st={st} :: {nombre}")
        if st is not None and ((200 <= st < 400) or st == 403):
            log_info(f"[resolve+chrome][cmg-day] {d} ELEGIDA shift+{k} ({carpeta}) st={st}")
            return u

    fallback = _cmg_url_for_shift(d, month_shift=0, base=base)
    log_warn(f"[resolve+chrome][cmg-day] {d} ninguna carpeta dio 2xx/3xx/403; usando fallback: {fallback}")
    return fallback


# ======================================================
# Función pública
# ======================================================
def descargar_cmg_rango(
    inicio: date,
    fin: date,
    carpeta: Path,
    max_workers: int = 4,
    max_shift: int = 2,
    usar_headless: bool = False,
    debug: bool = True,
) -> None:
    """
    CMG robusto:
    - Resuelve POR DÍA la carpeta YYYY/MM correcta (shift+0..max_shift).
    - Luego descarga el bloque (requests o Chrome según 403).
    - No cambia el path local: TODO queda en `carpeta`.
    """
    dias = [inicio + timedelta(days=i) for i in range((fin - inicio).days + 1)]
    urls: list[str] = []

    with _BrowserSession(carpeta, headless=usar_headless, debug=debug) as br:
        for d in dias:
            u = resolver_cmg_url_con_browser_por_dia(
                br,
                d,
                base="https://www.coordinador.cl/wp-content/uploads",
                max_shift=max_shift,
            )
            urls.append(u)

    _descargar_bloque_coordinador(
        urls,
        carpeta,
        max_workers=max_workers,
        usar_headless=usar_headless,
        debug=debug,
    )


# ======================================================
# Entry point standalone
# ======================================================
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="CMG Real - Descarga por rango de fechas")
    p.add_argument("--inicio",   type=str,  required=True, help="Fecha inicio YYYY-MM-DD")
    p.add_argument("--fin",      type=str,  required=True, help="Fecha fin YYYY-MM-DD")
    p.add_argument("--carpeta",  type=Path, default=Path("data/cmg_real"))
    p.add_argument("--workers",  type=int,  default=4)
    p.add_argument("--max-shift", type=int, default=2)
    args = p.parse_args()
    ini = datetime.strptime(args.inicio.strip(), "%Y-%m-%d").date()
    fin = datetime.strptime(args.fin.strip(), "%Y-%m-%d").date()
    descargar_cmg_rango(ini, fin, args.carpeta, args.workers, max_shift=args.max_shift)
