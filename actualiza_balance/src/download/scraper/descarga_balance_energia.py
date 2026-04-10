"""
descarga_balance_energia.py — Descarga del balance de energía desde PLABACOM (S3).
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from ._shared import (
    ARCHIVOS_NO_ENCONTRADOS,
    _carpeta_mes,
    _probe_ok,
    descargar_en_paralelo,
    log_error,
    log_info,
    log_warn,
    prioridad_descarga,
)

# ======================================================
# Constantes y helpers específicos de balance de energía
# ======================================================
PREFIJOS_BALANCE = ["01 Resultados", "02 Antecedentes de Cálculo", "03 Bases de Datos"]


def nombre_archivo_transferencias_economicas(prefijo: str, fecha: str, codigo: str = "BD01", ext: str = "zip"):
    return f"{prefijo}_{fecha}_{codigo}.{ext}"


def construye_plabacom_url(
    nombre_archivo: str,
    anio: int,
    mes: int | str,
    categoria="Energia",
    estado="Definitivo",
    version="v_1",
    base="https://cen-plabacom.s3.amazonaws.com",
) -> str:
    carpeta_mes = _carpeta_mes(mes)
    path = f"PLABACOM/{anio}/{carpeta_mes}/{categoria}/{estado}/{version}/{nombre_archivo}"
    return f"{base}/{quote(path, safe='/')}"


def encontrar_mes_disponible_te(anio: int, mes: int, max_retro: int = 12) -> tuple[int, int] | None:
    """Busca hacia atrás hasta 12 meses un mes que tenga '01 Resultados' disponible en S3."""
    for _ in range(max_retro):
        cod_fecha = f"{str(anio)[-2:]}{mes:02d}"
        probe = nombre_archivo_transferencias_economicas("01 Resultados", cod_fecha)
        url = construye_plabacom_url(probe, anio, mes)
        if _probe_ok(url):
            return anio, mes
        anio, mes = ((anio - 1, 12) if mes == 1 else (anio, mes - 1))
    return None


# ======================================================
# Función pública
# ======================================================
def descargar_balance_energia_plabacom(anio: int, mes: int, carpeta: Path) -> None:
    inicio_dt = datetime.now()
    log_info(f"Comienza descarga del balance de energía (solicitado {anio}-{mes:02d})")
    hallado = encontrar_mes_disponible_te(anio, mes)
    if not hallado:
        log_error("No se encontró ningún mes disponible para balance de energía.")
        return
    anio_ok, mes_ok = hallado
    if (anio_ok, mes_ok) != (anio, mes):
        log_warn(f"No hay datos para {anio}-{mes:02d}. Usando {anio_ok}-{mes_ok:02d}")

    cod_fecha = f"{str(anio_ok)[-2:]}{mes_ok:02d}"
    prioridad_descarga()
    urls = [
        construye_plabacom_url(nombre_archivo_transferencias_economicas(p, cod_fecha), anio_ok, mes_ok)
        for p in PREFIJOS_BALANCE
    ]
    descargar_en_paralelo(urls, max_workers=3, carpeta=carpeta)
    if ARCHIVOS_NO_ENCONTRADOS:
        log_warn(f"No descargados ({len(ARCHIVOS_NO_ENCONTRADOS)}):")
        for u in ARCHIVOS_NO_ENCONTRADOS:
            log_warn(f" - {u}")
    else:
        log_info(f"Balance de energía OK en {datetime.now() - inicio_dt}")


# ======================================================
# Entry point standalone
# ======================================================
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Balance de Energía - Descarga desde PLABACOM")
    p.add_argument("--anio",    type=int,  required=True)
    p.add_argument("--mes",     type=int,  required=True)
    p.add_argument("--carpeta", type=Path, default=Path("data/energia"))
    args = p.parse_args()
    descargar_balance_energia_plabacom(args.anio, args.mes, args.carpeta)
