"""
descarga_balance_sscc.py — Descarga del balance de SSCC desde PLABACOM (S3).
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

from ._shared import (
    ARCHIVOS_NO_ENCONTRADOS,
    _carpeta_mes,
    descargar_plabacom,
    log_info,
    log_warn,
    prioridad_descarga,
)

# ======================================================
# Constantes y helpers específicos de SSCC
# ======================================================
PREFIJOS_SSCC = "Balance_SSCC"


def nombre_archivo_sscc(prefijo: str, fecha: date, codigo: str = "def", ext: str = "zip"):
    nombre_mes_abreviado = fecha.strftime("%b").lower()
    return f"{prefijo}_{fecha.year}_{nombre_mes_abreviado}_{codigo}.{ext}"


def construye_plabacom_url_sscc(
    nombre_archivo: str,
    anio: int,
    mes: int | str,
    categoria="SSCC",
    estado="Definitivo",
    version="v_1",
    base="https://cen-plabacom.s3.amazonaws.com",
) -> str:
    carpeta_mes = _carpeta_mes(mes)
    path = f"PLABACOM/{anio}/{carpeta_mes}/{categoria}/{estado}/{version}/{nombre_archivo}"
    return f"{base}/{quote(path, safe='/')}"


# ======================================================
# Función pública
# ======================================================
def descargar_balance_sscc_plabacom(anio: int, mes: int, carpeta: Path) -> None:
    inicio_dt = datetime.now()
    log_info(f"Comienza descarga del balance de SSCC (solicitado {anio}-{mes:02d})")
    fecha = date(anio, mes, 1)
    nombre_archivo = nombre_archivo_sscc(PREFIJOS_SSCC, fecha)
    url = construye_plabacom_url_sscc(nombre_archivo, anio, mes)
    prioridad_descarga()
    descargar_plabacom(url, carpeta)
    if ARCHIVOS_NO_ENCONTRADOS:
        log_warn(f"No descargados ({len(ARCHIVOS_NO_ENCONTRADOS)}):")
        for u in ARCHIVOS_NO_ENCONTRADOS:
            log_warn(f" - {u}")
    else:
        log_info(f"Balance de SSCC OK en {datetime.now() - inicio_dt}")


# ======================================================
# Entry point standalone
# ======================================================
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Balance de SSCC - Descarga desde PLABACOM")
    p.add_argument("--anio",    type=int,  required=True)
    p.add_argument("--mes",     type=int,  required=True)
    p.add_argument("--carpeta", type=Path, default=Path("data/sscc"))
    args = p.parse_args()
    descargar_balance_sscc_plabacom(args.anio, args.mes, args.carpeta)
