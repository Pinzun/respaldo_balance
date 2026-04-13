from .._locale import MESES_ES
# sscc_pg.py — versión PostgreSQL de sscc.py
import time
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd


def preflight_sscc(fecha: str, tipo: str = "Definitivo", mode: str = "strict"):
    from actualiza_balance.src.core.mariaDB.sscc import preflight_sscc as _pf
    return _pf(fecha, tipo, mode)


def procesar_sscc(fecha: str, tipo: str = "Definitivo") -> None:
    from actualiza_balance.src.core.mariaDB.sscc import procesar_sscc as _ps
    return _ps(fecha, tipo)


def importar_sscc(cx: Any, cursor: Any, fecha: str) -> None:
    """PART1 (staging): carga a importar_mcp.sscc_rt e importar_mcp.sscc_infra [PostgreSQL]."""
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = MESES_ES[date.month]
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent
    ruta_carga = ruta_base / "data" / "processed" / "sscc" / str(año) / periodo

    rt_csv = ruta_carga / f"sscc_rt_{periodo}.csv"
    infra_csv = ruta_carga / f"sscc_infra_{periodo}.csv"

    for p in (rt_csv, infra_csv):
        if not p.exists():
            raise FileNotFoundError(f"Falta archivo requerido para staging SSCC: {p}")

    print(f"Importando sscc {año} {nombre_mes} (staging) [PostgreSQL]...")
    ini = time.time()

    # sscc_rt
    cursor.execute("TRUNCATE TABLE importar_mcp.sscc_rt;")
    col_rt = ["concepto", "empresa", "recibe", "paga", "sen"]
    df_rt = pd.read_csv(rt_csv)
    df_rt = df_rt.iloc[:, :5]
    df_rt.columns = col_rt
    buf1 = StringIO()
    df_rt.to_csv(buf1, index=False, header=True)
    buf1.seek(0)
    cursor.copy_expert(
        f"COPY importar_mcp.sscc_rt ({', '.join(col_rt)}) "
        "FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ',')",
        buf1,
    )

    # sscc_infra
    cursor.execute("TRUNCATE TABLE importar_mcp.sscc_infra;")
    col_infra = ["empresa", "remuneracion", "recaudacion", "neto"]
    df_infra = pd.read_csv(infra_csv)
    df_infra = df_infra.iloc[:, :4]
    df_infra.columns = col_infra
    buf2 = StringIO()
    df_infra.to_csv(buf2, index=False, header=True)
    buf2.seek(0)
    cursor.copy_expert(
        f"COPY importar_mcp.sscc_infra ({', '.join(col_infra)}) "
        "FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ',')",
        buf2,
    )

    cx.commit()
    final = time.time()
    print("sscc importado con éxito (staging) [PostgreSQL].")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")


def revisar_sscc(cursor: Any) -> None:
    print("Revisando sscc [PostgreSQL]...")

    e = """
        SELECT t.empresa
        FROM (SELECT DISTINCT empresa FROM importar_mcp.sscc_rt) t
        LEFT JOIN importar_mcp.empresa2 e2 ON e2.col_7 = t.empresa
        LEFT JOIN mercado_corto_plazo.empresa e ON e.nombre = e2.nombreempresa
        WHERE e.id IS NULL;
    """
    cursor.execute(e)
    reve = cursor.fetchall()
    if reve:
        print("REVISAR EMPRESAS SSCC_RT!")
        input("Presione ENTER para continuar...")

    e2 = """
        SELECT t.empresa
        FROM (SELECT DISTINCT empresa FROM importar_mcp.sscc_infra) t
        LEFT JOIN importar_mcp.empresa2 e2 ON e2.col_7 = t.empresa
        LEFT JOIN mercado_corto_plazo.empresa e ON e.nombre = e2.nombreempresa
        WHERE e.id IS NULL;
    """
    cursor.execute(e2)
    reve2 = cursor.fetchall()
    if reve2:
        print("REVISAR EMPRESAS SSCC_INFRA!")
        input("Presione ENTER para continuar...")


def cargar_sscc(
    cx: Any,
    cursor: Any,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """PART2 (final): inserta en mercado_corto_plazo.sscc_rt y mercado_corto_plazo.sscc_infra [PostgreSQL]. NO hace commit."""
    date = pd.to_datetime(fecha)
    año = date.year
    nombre_mes = MESES_ES[date.month]

    print(f"Cargando sscc {año} {nombre_mes} (final) [PostgreSQL]...")
    ini = time.time()

    carga_rt = f"""
        INSERT INTO mercado_corto_plazo.sscc_rt
        SELECT
            v.id,
            t.concepto,
            e.id,
            t.recibe,
            t.paga,
            t.sen
        FROM importar_mcp.sscc_rt t
        LEFT JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        LEFT JOIN importar_mcp.empresa2 e2
            ON e2.col_7 = t.empresa
        LEFT JOIN mercado_corto_plazo.empresa e
            ON e.nombre = e2.nombreempresa;
    """
    cursor.execute(carga_rt)

    carga_infra = f"""
        INSERT INTO mercado_corto_plazo.sscc_infra
        SELECT
            v.id,
            e.id,
            t.remuneracion,
            t.recaudacion,
            t.neto
        FROM importar_mcp.sscc_infra t
        LEFT JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        LEFT JOIN importar_mcp.empresa2 e2
            ON e2.col_7 = t.empresa
        LEFT JOIN mercado_corto_plazo.empresa e
            ON e.nombre = e2.nombreempresa;
    """
    cursor.execute(carga_infra)

    if not do_commit:
        print("⚠️  cargar_sscc ejecutado en modo DRY (sin commit; lo decide el main) [PostgreSQL].")

    final = time.time()
    print("sscc: INSERTs ejecutados [PostgreSQL].")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")
