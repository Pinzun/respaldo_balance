from .._locale import MESES_ES
# sobrecostos_pg.py — versión PostgreSQL de sobrecostos.py
import time
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd


def preflight_sobrecostos(fecha: str, mode: str = "strict"):
    from actualiza_balance.src.core.mariaDB.sobrecostos import preflight_sobrecostos as _pf
    return _pf(fecha, mode)


def procesar_sobrecostos(fecha: str) -> None:
    from actualiza_balance.src.core.mariaDB.sobrecostos import procesar_sobrecostos as _ps
    return _ps(fecha)


def importar_sobrecostos(cx: Any, cursor: Any, fecha: str) -> None:
    """PART1 (staging): TRUNCATE + COPY a importar_mcp.cv_importado e importar_mcp.sobrecostos [PostgreSQL]."""
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = MESES_ES[date.month]
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent.parent
    ruta_carga = ruta_base / "data" / "processed" / "energia" / str(año) / periodo

    cv_csv = ruta_carga / f"{periodo}_costosvariables.csv"
    sc_csv = ruta_carga / f"{periodo}_sobrecostos.csv"

    for p in (cv_csv, sc_csv):
        if not p.exists():
            raise FileNotFoundError(f"Falta archivo requerido para staging sobrecostos: {p}")

    print(f"Importando sobrecostos {año} {nombre_mes} (staging) [PostgreSQL]...")
    ini = time.time()

    # cv_importado
    cursor.execute("TRUNCATE TABLE importar_mcp.cv_importado;")
    col_cv = ["fecha", "hora", "unidadgen", "cv_usd_mwh"]
    df_cv = pd.read_csv(cv_csv)
    df_cv = df_cv.iloc[:, :4]
    df_cv.columns = col_cv
    buf1 = StringIO()
    df_cv.to_csv(buf1, index=False, header=True)
    buf1.seek(0)
    cursor.copy_expert(
        f"COPY importar_mcp.cv_importado ({', '.join(col_cv)}) "
        "FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ',')",
        buf1,
    )

    # sobrecostos
    cursor.execute("TRUNCATE TABLE importar_mcp.sobrecostos;")
    col_sc = ["fecha", "hora", "tipo", "unidadgen", "sobrecosto_clp",
              "zona_pago", "gen", "cons_propio", "cv", "cmg", "sscc"]
    df_sc = pd.read_csv(sc_csv)
    df_sc = df_sc.iloc[:, :11]
    df_sc.columns = col_sc
    buf2 = StringIO()
    df_sc.to_csv(buf2, index=False, header=True)
    buf2.seek(0)
    cursor.copy_expert(
        f"COPY importar_mcp.sobrecostos ({', '.join(col_sc)}) "
        "FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ',')",
        buf2,
    )

    cx.commit()
    final = time.time()
    print("Sobrecostos importados con éxito (staging) [PostgreSQL].")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")


def revisar_sobrecostos(cursor: Any) -> None:
    print("Revisando sobrecostos [PostgreSQL]...")

    revision1 = """
        SELECT t.unidadgen
        FROM (SELECT DISTINCT unidadgen FROM importar_mcp.cv_importado) t
        LEFT JOIN importar_mcp.unidadgen2 u2 ON u2.central = t.unidadgen
        LEFT JOIN mercado_corto_plazo.unidadgeneracion u ON u."Nombre" = u2.central_unidadgeneracion
        WHERE u.id IS NULL;
    """
    cursor.execute(revision1)
    rev1 = cursor.fetchall()
    if rev1:
        print("REVISAR UGEN CV!")
        input("Presione ENTER para continuar...")

    revision2 = """
        SELECT t.unidadgen
        FROM (SELECT DISTINCT unidadgen FROM importar_mcp.sobrecostos) t
        LEFT JOIN importar_mcp.unidadgen2 u2 ON u2.central = t.unidadgen
        LEFT JOIN mercado_corto_plazo.unidadgeneracion u ON u."Nombre" = u2.central_unidadgeneracion
        WHERE u.id IS NULL;
    """
    cursor.execute(revision2)
    rev2 = cursor.fetchall()
    if rev2:
        print("REVISAR UGEN SC!")
        input("Presione ENTER para continuar...")


def cargar_sobrecostos(
    cx: Any,
    cursor: Any,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """PART2 (final): inserta en mercado_corto_plazo.cv y mercado_corto_plazo.sobrecostos [PostgreSQL]. NO hace commit."""
    date = pd.to_datetime(fecha)
    año = date.year
    nombre_mes = MESES_ES[date.month]

    print(f"Cargando sobrecostos {año} {nombre_mes} (final) [PostgreSQL]...")
    ini = time.time()

    # DAY() → EXTRACT(DAY FROM ...)
    carga_cv = f"""
        INSERT INTO mercado_corto_plazo.cv
        SELECT DISTINCT
            v.id,
            hm.id,
            u.id,
            t.cv_usd_mwh
        FROM importar_mcp.cv_importado t
        LEFT JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        LEFT JOIN mercado_corto_plazo.hora_mensual hm
            ON hm.idversion = v.id
           AND hm.dia       = EXTRACT(DAY FROM t.fecha)
           AND hm.hora      = t.hora
           AND hm.minuto    = 0
        LEFT JOIN importar_mcp.unidadgen2 u2
            ON u2.central = t.unidadgen
        LEFT JOIN mercado_corto_plazo.unidadgeneracion u
            ON u."Nombre" = u2.central_unidadgeneracion;
    """
    cursor.execute(carga_cv)

    carga_sc = f"""
        INSERT INTO mercado_corto_plazo.sobrecostos
        SELECT DISTINCT
            v.id,
            hm.id,
            u.id,
            t.tipo,
            t.sobrecosto_clp,
            t.zona_pago,
            t.gen,
            t.cons_propio,
            t.cv,
            t.cmg,
            t.sscc
        FROM importar_mcp.sobrecostos t
        LEFT JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        LEFT JOIN mercado_corto_plazo.hora_mensual hm
            ON hm.idversion = v.id
           AND hm.dia       = EXTRACT(DAY FROM t.fecha)
           AND hm.hora      = t.hora
           AND hm.minuto    = 0
        LEFT JOIN importar_mcp.unidadgen2 u2
            ON u2.central = t.unidadgen
        LEFT JOIN mercado_corto_plazo.unidadgeneracion u
            ON u."Nombre" = u2.central_unidadgeneracion;
    """
    cursor.execute(carga_sc)

    if not do_commit:
        print("⚠️  cargar_sobrecostos ejecutado en modo DRY (sin commit; lo decide el main) [PostgreSQL].")

    final = time.time()
    print("Sobrecostos: INSERTs ejecutados [PostgreSQL].")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")
