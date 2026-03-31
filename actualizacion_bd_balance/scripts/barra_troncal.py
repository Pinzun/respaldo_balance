# scripts/barra_troncal.py

import os
import time
from pathlib import Path

import pandas as pd
from pymysql.connections import Connection
from pymysql.cursors import Cursor

from scripts.preflight_utils import PreflightItem, make_result, repo_root


def preflight_barrast(fecha: str, tipo: str = "Definitivo", mode: str = "skip"):
    """
    Preflight para barra_troncal (barrast).

    mode:
      - "skip": si faltan requeridos => marca SKIP (no ejecutable esta corrida)
      - "strict": si faltan requeridos => marca FAIL (error)
    """
    date = pd.to_datetime(fecha)
    año = date.year
    mes = date.month
    periodo = f"{str(año)[-2:]}{mes:02d}"

    root = repo_root()

    raw_dir = root / "data" / "raw" / "potencia" / str(año) / periodo
    processed_dir = root / "data" / "processed" / "potencia" / str(año) / periodo

    archivo_xlsm = raw_dir / f"Balance_{periodo}_def.xlsm"
    out_csv = processed_dir / f"{periodo}_barrast.csv"

    items = [
        PreflightItem("BARRAST raw dir", raw_dir, True),
        PreflightItem("BARRAST input xlsm", archivo_xlsm, True),
        PreflightItem("BARRAST processed dir (se crea)", processed_dir, False),
        PreflightItem("BARRAST output csv (se genera)", out_csv, False),
    ]

    r = make_result("barra_troncal", items)

    # Si tu preflight_utils ya trae skip/fail: esto calza perfecto.
    # Si no, mira el parche en la sección 2.
    if not r.ok:
        if mode == "skip":
            r.skip = True
            r.fail = False
        else:  # strict
            r.skip = False
            r.fail = True
    else:
        r.skip = False
        r.fail = False

    return r


def procesar_barrast(fecha: str) -> None:
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent
    ruta_raw = ruta_base / "data" / "raw"
    ruta_processed = ruta_base / "data" / "processed"

    ruta_carpeta_descarga = ruta_raw / "potencia" / f"{año}" / f"{periodo}"
    ruta_carpeta_carga = ruta_processed / "potencia" / f"{año}" / f"{periodo}"

    archivo = f"Balance_{periodo}_def.xlsm"

    print(f"Procesando archivo: {archivo}...")
    i = time.time()

    df = pd.read_excel(
        ruta_carpeta_descarga / archivo,
        sheet_name="04. ASOCIACIÓN DE BARRAS",
        usecols="C:D",
        skiprows=4,
    )

    df = df.drop_duplicates().dropna()

    os.makedirs(ruta_carpeta_carga, exist_ok=True)

    salida = ruta_carpeta_carga / f"{periodo}_barrast.csv"
    df.to_csv(salida, index=False, sep=",", encoding="utf-8")

    f = time.time()
    print(f"Archivo guardado en: {salida}")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(f - i))}.")


def importar_barrast(conexion: Connection, cursor: Cursor, fecha: str) -> None:
    """
    PART1 (staging): carga CSV a importar.barrast (se permite commit).
    """
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent
    ruta_processed = ruta_base / "data" / "processed" / "potencia" / f"{año}" / f"{periodo}"
    archivo_csv = (ruta_processed / f"{periodo}_barrast.csv").resolve()

    print(f"Importando barrast (staging) {periodo}...")
    i = time.time()

    cursor.execute("TRUNCATE TABLE importar.barrast;")

    query = f"""
        LOAD DATA LOCAL INFILE '{str(archivo_csv)}'
        INTO TABLE importar.barrast
        CHARACTER SET UTF8MB4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
        LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES;
    """
    cursor.execute(query)
    conexion.commit()  # staging OK

    f = time.time()
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(f - i))}.")


def revisar_barrast(cursor: Cursor) -> None:
    print("Revisando barrast...")

    query = """
        SELECT t.barra
        FROM (SELECT DISTINCT barra FROM importar.barrast) t
        LEFT JOIN importar.barra2 b2 ON b2.col_1 = t.barra
        LEFT JOIN balance.barra b ON b.nombre = b2.nombrebarra
        WHERE b.id IS NULL;
    """
    cursor.execute(query)
    revb = cursor.fetchall()
    if revb:
        print("REVISAR BARRAS (barra) EN barrast")
        input("Presione ENTER para continuar...")

    query2 = """
        SELECT t.barra_troncal
        FROM (SELECT DISTINCT barra_troncal FROM importar.barrast) t
        LEFT JOIN importar.barra2 b2 ON b2.col_1 = t.barra_troncal
        LEFT JOIN balance.barra b ON b.nombre = b2.nombrebarra
        WHERE b.id IS NULL;
    """
    cursor.execute(query2)
    revb2 = cursor.fetchall()
    if revb2:
        print("REVISAR BARRAS (barra_troncal) EN barrast")
        input("Presione ENTER para continuar...")


def cargar_barrast(
    conexion: Connection,
    cursor: Cursor,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """
    PART2 (final): inserta a balance.barra_troncal.
    NO hace commit: el main decide commit/rollback.
    """
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = date.month_name(locale="es_CL.utf8")
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"
    tipo_db = tipo.upper()

    print(f"Cargando barrast {periodo} ({nombre_mes} {año}) (tipo={tipo_db})...")
    i = time.time()

    query = f"""
        INSERT INTO balance.barra_troncal
        SELECT DISTINCT
            v.id,
            b.id,
            FIRST_VALUE(bb.id) OVER (PARTITION BY b.id ORDER BY bb.id ASC),
            ''
        FROM importar.barrast t
        JOIN balance.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo_db}'
        LEFT JOIN importar.barra2 b2
            ON b2.col_1 = t.barra
        LEFT JOIN balance.barra b
            ON b.nombre = b2.nombrebarra
        LEFT JOIN importar.barra2 b22
            ON b22.col_1 = t.barra_troncal
        LEFT JOIN balance.barra bb
            ON bb.nombre = b22.nombrebarra;
    """
    cursor.execute(query)

    if not do_commit:
        print("⚠️  cargar_barrast ejecutado en modo DRY (sin commit; lo decide el main).")

    f = time.time()
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(f - i))}.")