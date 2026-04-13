from .._locale import MESES_ES
# cmg_pg.py — versión PostgreSQL de cmg.py
import time
import logging
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd


def preflight_cmg(fecha: str, tipo: str = "Definitivo", mode: str = "strict"):
    from actualiza_balance.src.core.mariaDB.cmg import preflight_cmg as _pf
    return _pf(fecha, tipo, mode)


def procesar_cmg(fecha: str, tipo: str = "Definitivo") -> None:
    from actualiza_balance.src.core.mariaDB.cmg import procesar_cmg as _pc
    return _pc(fecha, tipo)


def importar_cmg(cx: Any, cursor: Any, fecha: str) -> None:
    """PART1 (staging): TRUNCATE + COPY a importar_mcp.cmg [PostgreSQL]."""
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = MESES_ES[date.month]
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent.parent
    ruta_processed = ruta_base / "data" / "processed" / "cmg" / f"{año}" / f"{periodo}"
    archivo_csv = ruta_processed / f"cmg{periodo}_15minutal.csv"

    logging.info(f"Importando cmg (staging) {nombre_mes} {año} [PostgreSQL]...")
    inicio = time.time()

    cursor.execute("TRUNCATE TABLE importar_mcp.cmg;")

    col_tabla = ["nombre_barra", "tension", "nombre_barra_cmg", "cuarto_hora",
                 "cmg_peso_kwh", "cmg_dolar_mwh", "dolar"]
    col_csv = ["nombre_barra", "tension", "nombre_barra_cmg", "Cuarto de Hora",
               "CMg[CLP/KWh]", "CMg[USD/MWh]", "USD"]

    df = pd.read_csv(archivo_csv, usecols=col_csv)
    df.columns = col_tabla

    buf = StringIO()
    df.to_csv(buf, index=False, header=True)
    buf.seek(0)
    cursor.copy_expert(
        f"COPY importar_mcp.cmg ({', '.join(col_tabla)}) "
        "FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ',')",
        buf,
    )
    cx.commit()

    final = time.time()
    logging.info("CMg importado con éxito [PostgreSQL].")
    logging.info(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")


def revisar_cmg(cursor: Any) -> None:
    logging.info("Revisando cmg [PostgreSQL]...")

    query = """
        SELECT t.nombre_barra_cmg
        FROM (SELECT DISTINCT nombre_barra_cmg FROM importar_mcp.cmg) t
        LEFT JOIN importar_mcp.barras_importadas bi
               ON bi."Barra" = t.nombre_barra_cmg
        LEFT JOIN mercado_corto_plazo.barra b
               ON b.nombre = bi."Nombre barra CNE"
        WHERE b.id IS NULL;
    """
    cursor.execute(query)
    revb = cursor.fetchall()

    if revb:
        logging.warning("REVISAR BARRAS CMG! Se encontraron inconsistencias [PostgreSQL].")
        for row in revb:
            logging.warning(f"Barra sin correspondencia: {row}")
        raise ValueError("Validación fallida: existen barras CMG sin correspondencia.")
    else:
        logging.info("Validación CMG completada sin inconsistencias [PostgreSQL].")


def cargar_cmg(
    cx: Any,
    cursor: Any,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """PART2 (final): inserta en mercado_corto_plazo.version y mercado_corto_plazo.cmg [PostgreSQL]. NO hace commit."""
    date = pd.to_datetime(fecha)
    año = date.year
    nombre_mes = MESES_ES[date.month]
    version = tipo[0].capitalize()

    logging.info(f"Cargando cmg {año} {nombre_mes} [PostgreSQL]...")
    inicio = time.time()

    # 1) Garantiza version
    cursor.execute(
        f"""
        INSERT INTO mercado_corto_plazo.version (periodo, tipo, nombre)
        VALUES ('{fecha}', '{tipo.upper()}', '{nombre_mes} {año} {version}')
        ON CONFLICT DO NOTHING;
        """
    )

    # 2) Inserta CMG
    cmg_insert = f"""
        INSERT INTO mercado_corto_plazo.cmg
            ("idVersion", hora_mensual, "idBarra", cmg_peso_kwh, cmg_dolar_mwh, dolar)
        SELECT DISTINCT
            v.id,
            t.cuarto_hora,
            b.id,
            t.cmg_peso_kwh,
            t.cmg_dolar_mwh,
            t.dolar
        FROM importar_mcp.cmg t
        JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        LEFT JOIN importar_mcp.barra2 bi
            ON bi.col_1 = t.nombre_barra_cmg
        LEFT JOIN mercado_corto_plazo.barra b
            ON b.nombre = bi.nombrebarra
        ON CONFLICT DO NOTHING;
    """
    cursor.execute(cmg_insert)

    if not do_commit:
        logging.warning("cargar_cmg ejecutado en modo DRY (sin commit; lo decide el main) [PostgreSQL].")

    final = time.time()
    logging.info("CMg: INSERT ejecutado [PostgreSQL].")
    logging.info(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")
