from .._locale import MESES_ES
# scripts/sobrecostos.py
import os
import time
from pathlib import Path

import pandas as pd
from pymysql.connections import Connection
from pymysql.cursors import Cursor

from actualiza_balance.src.core.preflight_utils import PreflightItem, make_result, repo_root

MESES_ES = {
1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

def preflight_sobrecostos(fecha: str, mode: str = "strict"):
    date = pd.to_datetime(fecha)
    año = date.year
    mes = date.month
    periodo = f"{str(año)[-2:]}{mes:02d}"

    root = repo_root()
    raw_dir = root / "data" / "raw" / "energia" / str(año) / periodo / "Detalles Diarios"
    processed_dir = root / "data" / "processed" / "energia" / str(año) / periodo

    cv_out = processed_dir / f"{periodo}_costosvariables.csv"
    sc_out = processed_dir / f"{periodo}_sobrecostos.csv"

    items = [
        PreflightItem("Sobrecostos raw Detalles Diarios dir", raw_dir, True),
        PreflightItem("Sobrecostos processed dir (se crea)", processed_dir, False),
        PreflightItem("CV output (se genera)", cv_out, False),
        PreflightItem("Sobrecostos output (se genera)", sc_out, False),
    ]
    return make_result("sobrecostos", items, mode=mode)

def procesar_sobrecostos(fecha: str) -> None:
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = MESES_ES[date.month]
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent.parent
    ruta_raw = ruta_base / "data" / "raw"
    ruta_processed = ruta_base / "data" / "processed"

    ruta_descarga = ruta_raw / "energia" / str(año) / periodo
    ruta_carga = ruta_processed / "energia" / str(año) / periodo

    ruta_carpeta_descarga = ruta_descarga / "Detalles Diarios"
    ruta_carpeta_carga = ruta_carga

    print(f"Procesando detalles diarios {año} {nombre_mes}...")
    inicio = time.time()

    archivos = list(ruta_carpeta_descarga.glob("*.xlsx"))
    if not archivos:
        raise FileNotFoundError(f"No se encontraron .xlsx en: {ruta_carpeta_descarga}")

    cv = pd.DataFrame()
    sobrecostos = pd.DataFrame()

    for archivo in archivos:
        # --- CV ---
        df1 = pd.read_excel(archivo, sheet_name="CV", usecols="A", header=None)
        start = None
        for idx, val in df1[0].items():
            if str(val) == "Fecha":
                start = idx
                break
        if start is None:
            continue

        df1 = (
            pd.read_excel(
                archivo,
                sheet_name="CV",
                skiprows=start,
                usecols="A:D",
            )
            .dropna()
        )
        cv = pd.concat([cv, df1], axis=0, ignore_index=True)

        # --- Sobrecostos ---
        df2 = pd.read_excel(archivo, sheet_name="Sobrecostos", usecols="A", header=None)
        start2 = None
        for idx, val in df2[0].items():
            if str(val) == "Fecha":
                start2 = idx
                break
        if start2 is None:
            continue

        df2 = (
            pd.read_excel(
                archivo,
                sheet_name="Sobrecostos",
                skiprows=start2,
                usecols="A:K",
            )
            .dropna()
        )
        sobrecostos = pd.concat([sobrecostos, df2], axis=0, ignore_index=True)

    os.makedirs(ruta_carpeta_carga, exist_ok=True)

    cv_salida = ruta_carpeta_carga / f"{periodo}_costosvariables.csv"
    sc_salida = ruta_carpeta_carga / f"{periodo}_sobrecostos.csv"

    cv.to_csv(cv_salida, index=False, encoding="utf-8", sep=",", decimal=".")
    sobrecostos.to_csv(sc_salida, index=False, encoding="utf-8", sep=",", decimal=".")

    fin = time.time()
    print(f"Archivos guardados en: {ruta_carpeta_carga}")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(fin - inicio))}.")


def importar_sobrecostos(cx: Connection, cursor: Cursor, fecha: str) -> None:
    """
    PART1 (staging): TRUNCATE + LOAD a tablas importar.*.
    Aquí SÍ hacemos commit.
    """
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = MESES_ES[date.month]
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent
    ruta_carga = ruta_base / "data" / "processed" / "energia" / str(año) / periodo

    cv_csv = (ruta_carga / f"{periodo}_costosvariables.csv").resolve()
    archivo_cv_csv_str = str(cv_csv).replace("\\", "/")
    sc_csv = (ruta_carga / f"{periodo}_sobrecostos.csv").resolve()
    archivo_sc_csv_str = str(sc_csv).replace("\\", "/")


    for p in (cv_csv, sc_csv):
        if not p.exists():
            raise FileNotFoundError(f"Falta archivo requerido para staging sobrecostos: {p}")

    print(f"Importando sobrecostos {año} {nombre_mes} (staging)...")
    ini = time.time()

    # Truncar tablas (estructura definida en crea_importar.sql)
    cursor.execute("TRUNCATE TABLE importar.cv_importado;")
    query1 = f"""
        LOAD DATA LOCAL INFILE '{archivo_cv_csv_str}'
        INTO TABLE importar.cv_importado
        CHARACTER SET UTF8MB4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
        LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES;
    """
    cursor.execute(query1)

    cursor.execute("TRUNCATE TABLE importar.sobrecostos;")
    query2 = f"""
        LOAD DATA LOCAL INFILE '{archivo_sc_csv_str}'
        INTO TABLE importar.sobrecostos
        CHARACTER SET UTF8MB4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
        LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES;
    """
    cursor.execute(query2)

    cx.commit()

    final = time.time()
    print("Sobrecostos importados con éxito (staging).")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")


def revisar_sobrecostos(cursor: Cursor) -> None:
    print("Revisando sobrecostos...")

    revision1 = """
        SELECT t.unidadgen
        FROM (SELECT DISTINCT unidadgen FROM importar.cv_importado) t
        LEFT JOIN importar.unidadgen2 u2 ON u2.central = t.unidadgen
        LEFT JOIN balance.unidadgeneracion u ON u.Nombre = u2.central_unidadgeneracion
        WHERE u.id IS NULL;
    """
    cursor.execute(revision1)
    rev1 = cursor.fetchall()
    if rev1:
        print("REVISAR UGEN CV!")
        input("Presione ENTER para continuar...")

    revision2 = """
        SELECT t.unidadgen
        FROM (SELECT DISTINCT unidadgen FROM importar.sobrecostos) t
        LEFT JOIN importar.unidadgen2 u2 ON u2.central = t.unidadgen
        LEFT JOIN balance.unidadgeneracion u ON u.Nombre = u2.central_unidadgeneracion
        WHERE u.id IS NULL;
    """
    cursor.execute(revision2)
    rev2 = cursor.fetchall()
    if rev2:
        print("REVISAR UGEN SC!")
        input("Presione ENTER para continuar...")


def cargar_sobrecostos(
    cx: Connection,
    cursor: Cursor,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """
    PART2 (final): inserta en balance.cv y balance.sobrecostos.
    NO hace commit: el main decide commit/rollback.
    """
    date = pd.to_datetime(fecha)
    año = date.year
    nombre_mes = MESES_ES[date.month]

    print(f"Cargando sobrecostos {año} {nombre_mes} (final)...")
    ini = time.time()

    carga_cv = f"""
        INSERT INTO balance.cv
        SELECT DISTINCT
            v.id,
            hm.id,
            u.id,
            t.cv_usd_mwh
        FROM importar.cv_importado t
        LEFT JOIN balance.`version` v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        LEFT JOIN balance.hora_mensual hm
            ON hm.idversion = v.id
           AND hm.dia       = DAY(t.fecha)
           AND hm.hora      = t.hora
           AND hm.minuto    = 0
        LEFT JOIN importar.unidadgen2 u2
            ON u2.central = t.unidadgen
        LEFT JOIN balance.unidadgeneracion u
            ON u.Nombre = u2.central_unidadgeneracion;
    """

    cursor.execute(carga_cv)

    carga_sc = f"""
        INSERT INTO balance.sobrecostos
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
        FROM importar.sobrecostos t
        LEFT JOIN balance.`version` v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        LEFT JOIN balance.hora_mensual hm
            ON hm.idversion = v.id
           AND hm.dia       = DAY(t.fecha)
           AND hm.hora      = t.hora
           AND hm.minuto    = 0
        LEFT JOIN importar.unidadgen2 u2
            ON u2.central = t.unidadgen
        LEFT JOIN balance.unidadgeneracion u
            ON u.Nombre = u2.central_unidadgeneracion;
    """
    cursor.execute(carga_sc)

    if not do_commit:
        print("⚠️  cargar_sobrecostos ejecutado en modo DRY (sin commit; lo decide el main).")

    final = time.time()
    print("Sobrecostos: INSERTs ejecutados.")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")