# scripts/cmg.py
import os
import time
from pymysql.connections import Connection
from pymysql.cursors import Cursor
from pathlib import Path
import pandas as pd
from actualiza_balance.src.core.preflight_utils import PreflightItem, make_result, repo_root
import logging
from typing import Any

def preflight_cmg(fecha: str, tipo: str = "Definitivo", mode: str = "strict"):
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    root = repo_root()
    raw_dir = root / "data" / "raw" / "cmg" / str(año) / periodo
    processed_dir = root / "data" / "processed" / "cmg" / str(año) / periodo

    archivo = f"cmg{periodo}_15min_formateado.csv"
    in_file = raw_dir / archivo
    out_file = processed_dir / f"cmg{periodo}_15minutal.csv"  # (opcional informativo)

    items = [
        PreflightItem("CMG raw dir", raw_dir, must_exist=True),
        PreflightItem("CMG input file", in_file, must_exist=True),
        # output dir no es “must exist” porque lo creas tú
        PreflightItem("CMG processed dir (se crea si falta)", processed_dir, must_exist=False),
        PreflightItem("CMG output file (se generará)", Path(str(out_file)), must_exist=False),
    ]
    return make_result("cmg", items, mode=mode)


def procesar_cmg(fecha: str, tipo: str = "Definitivo") -> None:
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"
    version = tipo[:3].lower()

    root = repo_root()
    raw_dir = root / "data" / "raw" / "cmg" / str(año) / periodo
    processed_dir = root / "data" / "processed" / "cmg" / str(año) / periodo
    os.makedirs(processed_dir, exist_ok=True)

    archivo = f"cmg{periodo}_15min_formateado.csv"
    in_file = raw_dir / archivo
    out_file = processed_dir / f"cmg{periodo}_15minutal.csv"  # (opcional informativo)

    ruta_carpeta_descarga = raw_dir / "cmg" / str(año)
    ruta_carpeta_carga = processed_dir / "cmg" / str(año)

    archivo = f"cmg{periodo}_15min_formateado.csv"

    logging.info(f"Procesando archivo: {archivo}")
    inicio = time.time()

    df = pd.read_csv(
        (in_file),
        parse_dates=["FECHA"],
        sep=";",
    )

    # OJO: 'periodo' y 'DIA' se recalculan desde FECHA
    df["periodo"] = df["FECHA"].dt.strftime("%Y-%m-01")
    df["DIA"] = df["FECHA"].dt.strftime("%d")

    columnas = [
        "nombre_barra",
        "tension",
        "nombre_barra_cmg",
        "periodo",
        "Cuarto de Hora",
        "DIA",
        "HORA",
        "MINUTO",
        "CMg[CLP/KWh]",
        "CMg[USD/MWh]",
        "USD",
    ]

    cmg = df[columnas].copy()
    del df

    os.makedirs(ruta_carpeta_carga, exist_ok=True)

    cmg.to_csv(
        out_file,
        index=False,
        encoding="utf-8",
        sep=",",
        decimal=".",
    )
    del cmg

    final = time.time()
    logging.info(f"Archivo guardado en: {out_file}")
    logging.info(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")


def importar_cmg(cx: Connection, cursor: Cursor, fecha: str) -> None:
    """
    PART1 (staging): TRUNCATE + LOAD a importar.cmg.
    Aquí sí se permite commit.
    """
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = date.month_name(locale="es_CL.utf8")
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent
    ruta_processed = ruta_base / "data" / "processed" / "cmg" / f"{año}" / f"{periodo}"
    archivo_csv = (ruta_processed / f"cmg{periodo}_15minutal.csv").resolve()
    # Normalizar la ruta para MySQL
    archivo_csv_str = str(archivo_csv).replace("\\", "/")

    logging.info(f"Importando cmg (staging) {nombre_mes} {año}...")
    inicio = time.time()

    # Truncar tabla (estructura definida en crea_importar.sql)
    cursor.execute("TRUNCATE TABLE importar.cmg;")

    query = f"""
        LOAD DATA LOCAL INFILE '{archivo_csv_str}'
        INTO TABLE importar.cmg
        CHARACTER SET UTF8MB4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
        LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES;
    """
    cursor.execute(query)
    cx.commit()  # staging OK

    final = time.time()
    logging.info("CMg importado con éxito.")
    logging.info(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")


def revisar_cmg(cursor: Any) -> None:
    logging.info("Revisando cmg...")

    query = """
        SELECT t.nombre_barra_cmg
        FROM (SELECT DISTINCT nombre_barra_cmg FROM importar.cmg) t
        LEFT JOIN importar.barras_importadas bi 
               ON bi.Barra = t.nombre_barra_cmg
        LEFT JOIN balance.barra b 
               ON b.nombre = bi.`Nombre barra CNE`
        WHERE b.id IS NULL;
    """
    cursor.execute(query)
    revb = cursor.fetchall()

    if revb:
        logging.warning("REVISAR BARRAS CMG! Se encontraron inconsistencias.")
        for (nombre_barra_cmg,) in revb:
            logging.warning(f"Barra sin correspondencia: {nombre_barra_cmg}")
        raise ValueError("Validación fallida: existen barras CMG sin correspondencia.")
    else:
        logging.info("Validación CMG completada sin inconsistencias.")



def cargar_cmg( 
    cx: Connection,
    cursor: Cursor,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """
    PART2 (final): inserta en balance.version (si no existe) y balance.cmg.
    NO hace commit. El main decide commit/rollback.

    Nota: NO crea hora_mensual aquí, porque el staging de cmg no trae fecha_hora.
    """
    date = pd.to_datetime(fecha)
    año = date.year
    nombre_mes = date.month_name(locale="es_CL.utf8")
    version = tipo[0].capitalize()

    logging.info(f"Cargando cmg {año} {nombre_mes}...")
    inicio = time.time()

    # 1) Garantiza version (sin inventar IDs a mano si no es estrictamente necesario)
    # Si 'id' es AUTO_INCREMENT, elimina el campo id del insert.
    cursor.execute(
        f"""
        INSERT IGNORE INTO balance.version (periodo, tipo, nombre)
        VALUES ('{fecha}', '{tipo.upper()}', '{nombre_mes} {año} {version}');
        """
    )

    # 2) Inserta CMG
    cmg_insert = f"""
        INSERT IGNORE INTO balance.cmg
            (idVersion, hora_mensual, idBarra, cmg_peso_kwh, cmg_dolar_mwh, dolar)
        SELECT DISTINCT
            v.id,
            t.`Cuarto de Hora`,
            b.id,
            t.`CMg[CLP/KWh]`,
            t.`CMg[USD/MWh]`,
            t.USD
        FROM importar.cmg t
        JOIN balance.`version` v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        LEFT JOIN importar.barras_importadas bi
            ON bi.col_1 = t.nombre_barra_cmg
        LEFT JOIN balance.barra b
            ON b.nombre = bi.nombrebarra;
    """
    cursor.execute(cmg_insert)

    if not do_commit:
        logging.warning("cargar_cmg ejecutado en modo DRY (sin commit; lo decide el main).")

    final = time.time()
    logging.info("CMg: INSERT ejecutado.")
    logging.info(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")
