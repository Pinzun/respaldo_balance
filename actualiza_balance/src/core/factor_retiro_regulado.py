# scripts/factor_retiro_regulado.py
import os
import time
from pathlib import Path

import pandas as pd
from pymysql.connections import Connection
from pymysql.cursors import Cursor

from actualiza_balance.src.core.preflight_utils import PreflightItem, make_result, repo_root

def preflight_frr(fecha: str, mode: str = "strict"):
    date = pd.to_datetime(fecha)
    año = date.year
    mes = date.month
    periodo = f"{str(año)[-2:]}{mes:02d}"

    root = repo_root()
    raw_dir = root / "data" / "raw" / "energia" / str(año) / periodo
    processed_dir = root / "data" / "processed" / "energia" / str(año) / periodo

    # nombre según tu regla actual
    if año >= 2025 and mes >= 5:
        xls = raw_dir / f"Asig_dev_IT_{periodo}_def.xlsm"
    else:
        xls = raw_dir / f"Balance_{periodo}_BD01.xlsm"

    out_csv = processed_dir / f"retiroregulado_{periodo}.csv"

    items = [
        PreflightItem("FRR raw dir", raw_dir, True),
        PreflightItem("FRR input xlsm", xls, True),
        PreflightItem("FRR processed dir (se crea)", processed_dir, False),
        PreflightItem("FRR output csv (se genera)", out_csv, False),
    ]
    return make_result("factor_retiro_regulado", items, mode=mode)

def procesar_frr(fecha: str) -> None:
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent
    ruta_raw = ruta_base / "data" / "raw"
    ruta_processed = ruta_base / "data" / "processed"

    # Fuente (excel) y salida (csv)
    ruta_carpeta_descarga = ruta_raw / "energia" / str(año) / periodo
    ruta_carpeta_carga = ruta_processed / "energia" / str(año) / periodo

    if año >= 2025 and numero_mes >= 5:
        archivo = f"Asig_dev_IT_{periodo}_def.xlsm"
    else:
        archivo = f"Balance_{periodo}_BD01.xlsm"

    print(f"Procesando {archivo}...")
    inicio = time.time()

    os.makedirs(ruta_carpeta_carga, exist_ok=True)

    # Nota: mantengo tu lógica “antigua”, leyendo desde raw
    if (año < 2023) or (año == 2022 and numero_mes <= 12):
        df = pd.read_excel(
            ruta_carpeta_descarga / archivo,
            sheet_name="ASIGNACIÓN Dx",
            usecols="A:H",
            skiprows=5,
        )
        df["kWh Punto Suministro2"] = 0
        df["%2"] = 0
        df = df[
            [
                "Bloque Regulado",
                "Suministrador",
                "kWh Punto Suministro",
                "%",
                "kWh Punto Suministro2",
                "%2",
                "Físico [kWh]",
                "Monetario [$]",
            ]
        ]
    else:
        df = pd.read_excel(
            ruta_carpeta_descarga / archivo,
            sheet_name="ASIGNACIÓN Dx",
            usecols="A:H",
            skiprows=5,
        )

    df = df.dropna()

    salida_csv = (ruta_carpeta_carga / f"retiroregulado_{periodo}.csv").resolve()
    df.to_csv(
        salida_csv,
        index=False,
        sep=",",
        decimal=".",
        encoding="utf-8",
    )

    final = time.time()
    print(f"Archivo guardado en: {salida_csv}")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")


def importar_frr(cx: Connection, cursor: Cursor, fecha: str) -> None:
    """
    PART1 (staging): TRUNCATE + LOAD a _egulado.
    Aquí SÍ hacemos commit, porque staging se regenera.
    """
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = date.month_name(locale="es_CL.utf8")
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent
    ruta_processed = ruta_base / "data" / "processed" / "energia" / str(año) / periodo
    archivo_csv = (ruta_processed / f"retiroregulado_{periodo}.csv").resolve()
    archivo_csv_str = str(archivo_csv).replace("\\", "/")

    if not archivo_csv.exists():
        raise FileNotFoundError(f"No existe el CSV de retiro regulado esperado: {archivo_csv}")

    print(f"Importando Retiro Regulado {nombre_mes} {año} (staging)...")
    inicio = time.time()


    # 1. Crear tabla si no existe
    create_table_query = """ 
        CREATE TABLE IF NOT EXISTS importar.retiro_regulado (
            bloque_regulado     VARCHAR(100) NOT NULL,
            suministrador       VARCHAR(100) NOT NULL,
            kwh_ps1             FLOAT,
            porcentaje_ps1      FLOAT,
            kwh_ps2             FLOAT,
            porcentaje_ps2      FLOAT,
            fisico_kwh          FLOAT,
            monetario           FLOAT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    cursor.execute(create_table_query)


    cursor.execute("TRUNCATE TABLE importar.retiro_regulado;")

    query = f"""
        LOAD DATA LOCAL INFILE '{archivo_csv_str}'
        INTO TABLE importar.retiro_regulado
        CHARACTER SET UTF8MB4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
        LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES;
    """
    cursor.execute(query)
    cx.commit()

    final = time.time()
    print("Retiro Regulado importado con éxito (staging).")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")


def revisar_frr(cursor: Cursor) -> None:
    print("Revisando datos Retiro Regulado...")

    query = """
        SELECT t.bloque_regulado
        FROM (SELECT DISTINCT bloque_regulado FROM importar.retiroregulado) t
        LEFT JOIN importar.empresa2 e2 ON e2.col_7 = t.bloque_regulado
        LEFT JOIN balance.empresa e ON e.nombre = e2.nombreempresa
        WHERE e.id IS NULL;
    """
    cursor.execute(query)
    rev1 = cursor.fetchall()

    if rev1:
        print("REVISAR BLOQUE REGULADO")
        input("Presione ENTER para continuar...")

    query1 = """
        SELECT t.suministrador
        FROM (SELECT DISTINCT suministrador FROM importar.retiroregulado) t
        LEFT JOIN importar.empresa2 e2 ON e2.col_7 = t.suministrador
        LEFT JOIN balance.empresa e ON e.nombre = e2.nombreempresa
        WHERE e.id IS NULL;
    """
    cursor.execute(query1)
    rev2 = cursor.fetchall()

    if rev2:
        print("REVISAR SUMINISTRADORES")
        input("Presione ENTER para continuar...")


def cargar_frr(
    cx: Connection,
    cursor: Cursor,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """
    PART2 (final): inserta en balance.retiro_regulado_factor.
    NO hace commit: el main decide commit/rollback.
    """
    date = pd.to_datetime(fecha)
    nombre_mes = date.month_name(locale="es_CL.utf8")
    año = date.year

    print(f"Cargando Retiro Regulado {nombre_mes} {año} (final)...")
    inicio = time.time()

    query = f"""
        INSERT IGNORE INTO balance.retiro_regulado
        SELECT
            v.id,
            e.id,
            e2.id,
            r.kwh_ps1,
            r.`%_ps1`,
            r.kwh_ps2,
            r.`%_ps2`,
            r.fisico_kwh,
            r.monetario
        FROM importar.retiroregulado r
        JOIN balance.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        JOIN importar.empresa2 e3
            ON e3.col_7 = r.bloque_regulado
        JOIN balance.empresa e
            ON e.nombre = e3.nombreempresa
        JOIN importar.empresa2 e4
            ON e4.col_7 = r.suministrador
        JOIN balance.empresa e2
            ON e2.nombre = e4.nombreempresa;
    """
    cursor.execute(query)

    if not do_commit:
        print("⚠️  cargar_frr ejecutado en modo DRY (sin commit; lo decide el main).")

    final = time.time()
    print("Retiro Regulado: INSERT ejecutado.")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")