"""
descarga_politicas_operacion.py — Descarga de Políticas de Operación por rango de fechas desde coordinador.cl.
"""
from __future__ import annotations

import argparse
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
# Helpers específicos de Políticas de Operación
# ======================================================
def construye_politicas_operacion_url(
    d: date,
    base="https://www.coordinador.cl/wp-content/uploads",
) -> str:
    if d.day == 1:
        fecha_referencia = d - timedelta(days=1)
    else:
        fecha_referencia = d
    url = f"{base}/{fecha_referencia:%Y/%m}/PROGRAMA{d:%Y%m%d}.zip"
    return _normalize_coordinador_host(url)


def construye_politicas_operacion_url_variantes(
    d: date,
    base="https://www.coordinador.cl/wp-content/uploads",
    max_suffix: int = 3,
) -> list[str]:
    """Devuelve las variantes en orden: -max_suffix ... -1, y al final sin sufijo."""
    base_url = construye_politicas_operacion_url(d, base=base)
    variantes: list[str] = []
    for k in range(max_suffix, 0, -1):
        variantes.append(base_url.replace(".zip", f"-{k}.zip"))
    variantes.append(base_url)
    return variantes


def resolver_politicas_operacion_url_con_browser(
    br: "_BrowserSession",
    d: date,
    base="https://www.coordinador.cl/wp-content/uploads",
    max_suffix: int = 3,
) -> str:
    variantes = construye_politicas_operacion_url_variantes(d, base=base, max_suffix=max_suffix)

    for u in variantes:
        nombre = u.split("/")[-1]
        log_info(f"[resolve+chrome] {d} probando {nombre} (HEAD/fetch) ...")
        try:
            st = br.probe_status_head(u, timeout=20)
            if st is not None and 200 <= st < 400:
                log_info(f"[resolve+chrome] {d} ELEGIDA {nombre} (st={st})")
                return u
            log_info(f"[resolve+chrome] {d} descartada {nombre} (st={st})")
        except Exception as e:
            log_warn(f"[resolve+chrome] {d} fallo probando {nombre}: {e}")

    log_warn(f"[resolve+chrome] {d} ninguna variante dio 2xx/3xx; usando fallback sin sufijo")
    return variantes[-1]


# ======================================================
# Función pública
# ======================================================
def descargar_politicas_operacion_rango(
    inicio: date,
    fin: date,
    carpeta: Path,
    max_workers: int = 4,
    max_suffix: int = 3,
    usar_headless: bool = False,
    debug: bool = True,
) -> None:
    """
    1) Resolver, por día, cuál variante (-3/-2/-1/base) existe usando UNA sola ventana Chrome.
    2) Descargar el bloque completo UNA sola vez con _descargar_bloque_coordinador().
    """
    dias = [inicio + timedelta(days=i) for i in range((fin - inicio).days + 1)]

    urls_resueltas: list[str] = []
    with _BrowserSession(carpeta, headless=usar_headless, debug=debug) as br:
        for d in dias:
            u = resolver_politicas_operacion_url_con_browser(
                br, d,
                base="https://www.coordinador.cl/wp-content/uploads",
                max_suffix=max_suffix,
            )
            urls_resueltas.append(u)

    _descargar_bloque_coordinador(
        urls_resueltas,
        carpeta,
        max_workers=max_workers,
        usar_headless=usar_headless,
        debug=debug,
    )


# ======================================================
# Entry point standalone
# ======================================================
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Políticas de Operación - Descarga por rango de fechas")
    p.add_argument("--inicio",     type=str,  required=True, help="Fecha inicio YYYY-MM-DD")
    p.add_argument("--fin",        type=str,  required=True, help="Fecha fin YYYY-MM-DD")
    p.add_argument("--carpeta",    type=Path, required=True)
    p.add_argument("--workers",    type=int,  default=4)
    p.add_argument("--max-suffix", type=int,  default=3)
    args = p.parse_args()
    ini = datetime.strptime(args.inicio.strip(), "%Y-%m-%d").date()
    fin = datetime.strptime(args.fin.strip(), "%Y-%m-%d").date()
    descargar_politicas_operacion_rango(ini, fin, args.carpeta, args.workers, args.max_suffix)
