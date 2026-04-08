# scripts/cv_op.py
import os
import time
from calendar import monthrange
from datetime import datetime
from pathlib import Path

import pandas as pd
from pymysql.connections import Connection
from pymysql.cursors import Cursor

from scripts.preflight_utils import PreflightItem, make_result, repo_root

def preflight_cv_op(fecha: str, mode: str = "strict"):
    date = pd.to_datetime(fecha)
    año = date.year
    mes = date.month
    periodo = f"{str(año)[-2:]}{mes:02d}"

    root = repo_root()
    raw_dir = root / "data" / "raw" / "operacion" / str(año) / periodo
    processed_dir = root / "data" / "processed" / "operacion" / str(año) / periodo

    # PO diarios: no listamos todos aquí (sería mucho), validamos carpeta y uno de ejemplo.
    sample = raw_dir / f"PO{periodo}01.xlsx"
    out_csv = processed_dir / f"cv_op_{periodo}.csv"

    items = [
        PreflightItem("CV_OP raw dir", raw_dir, True),
        PreflightItem("CV_OP sample PO file (PO...01.xlsx)", sample, False),  # lo dejo OPT
        PreflightItem("CV_OP processed dir (se crea)", processed_dir, False),
        PreflightItem("CV_OP output csv (se genera)", out_csv, False),
    ]
    return make_result("cv_op", items, mode=mode)

def procesar_po(fecha: str) -> None:
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = date.month_name(locale="es_CL.utf8")
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent
    ruta_raw = ruta_base / "data" / "raw"
    ruta_processed = ruta_base / "data" / "processed"

    ruta_carpeta_descarga = ruta_raw / "operacion" / str(año) / periodo
    ruta_carpeta_carga = ruta_processed / "operacion" / str(año) / periodo

    os.makedirs(ruta_carpeta_carga, exist_ok=True)

    _, dias = monthrange(año, numero_mes)

    programa = []
    print(f"Procesando programas de operación {nombre_mes} {año}...")
    ini = time.time()

    for dia in range(1, dias + 1):
        po = f"PO{periodo}{dia:02d}.xlsx"
        print(f"Leyendo archivo {po}...")

        df = pd.read_excel(
            ruta_carpeta_descarga / po,
            sheet_name="RESUMEN",
            header=None,
            )

        idx = df[df[1] == "2. CENTRALES TÉRMICAS (datos diarios)"].index[0]
        inicio = idx + 5
        fin = df[df[1] == "Total"].index[0]

        columnas1 = [
            "ugen", "e_max", "energia", "cv", "cvc", "cvnc", "cmedmt",
            "costocombust", "unidadcombust", "tiempopartida",
            "partidafriac", "partidafriat", "partidatibiac", "partidatibiat",
            "partidatibia2c", "partidatibia2t",
            "partidacalientec", "partidacalientet", "costodetencion",
        ]
        columnas2 = [
            "ugen", "e_max", "energia", "cv", "cvc", "cvnc", "cmedmt",
            "costocombust", "unidadcombust", "tiempopartida",
            "partidafriac", "partidafriat", "partidatibiac", "partidatibiat",
            "partidacalientec", "partidacalientet", "costodetencion",
        ]

        if datetime(año, numero_mes, dia) >= datetime(2025, 4, 18):
            tabla = df.loc[inicio:fin - 1, list(range(1, 20))]
            tabla.columns = columnas1
        else:
            tabla = df.loc[inicio:fin - 1, list(range(1, 18))]
            tabla.columns = columnas2
            tabla["partidatibia2c"] = "-"
            tabla["partidatibia2t"] = "-"
            tabla = tabla[columnas1]

        tabla["dia"] = dia
        tabla["periodo"] = datetime(año, numero_mes, 1)
        programa.append(tabla)

    programa_final = pd.concat(programa, ignore_index=True)
    archivo_salida = f"cv_op_{periodo}.csv"
    salida = ruta_carpeta_carga / archivo_salida

    programa_final.to_csv(
        salida,
        index=False,
        sep=",",
        decimal=".",
        encoding="utf-8",
    )

    end = time.time()
    print(f"Archivo guardado en {salida}.")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(end - ini))}.")


def importar_cv_op(cx: Connection, cursor: Cursor, fecha: str) -> None:
    """
    PART1 (staging): TRUNCATE + LOAD a importar.cv_op.
    Aquí SÍ hacemos commit, porque staging se regenera.
    """
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = date.month_name(locale="es_CL.utf8")
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent
    ruta_processed = ruta_base / "data" / "processed" / "operacion" / str(año) / periodo
    archivo_csv = (ruta_processed / f"cv_op_{periodo}.csv").resolve()
    archivo_csv_str = str(archivo_csv).replace("\\", "/")

    if not archivo_csv.exists():
        raise FileNotFoundError(f"No existe el CSV de cv_op esperado: {archivo_csv}")

    print(f"Importando cv_op {año} {nombre_mes} (staging)...")
    ini = time.time()

    #Crear tabla cv_op si no existe
    create_table_query="""
       CREATE TABLE IF NOT EXISTS importar.cv_op (
        central             VARCHAR(255) NOT NULL,
        e_max               FLOAT,
        energia             FLOAT,
        cv                  FLOAT,
        cvc                 FLOAT,
        cvnc                FLOAT,
        cmedmt              FLOAT,
        costocombust        FLOAT,
        unidadcombust       VARCHAR(50),
        tiempopartida       FLOAT,
        partidafriac        FLOAT,
        partidafriat        VARCHAR(50),
        partidatibiac       FLOAT,
        partidatibiat       VARCHAR(50),
        partidatibia2c      FLOAT,
        partidatibia2t      VARCHAR(50),
        partidacalientec    FLOAT,
        partidaclaientet    VARCHAR(50),
        costodetencion      FLOAT,
        hora                INT,
        fecha               DATE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

    """
    cursor.execute(create_table_query)

    cursor.execute("TRUNCATE TABLE importar.cv_op;")

    query = f"""
        LOAD DATA LOCAL INFILE '{archivo_csv_str}'
        INTO TABLE importar.cv_op
        CHARACTER SET UTF8MB4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
        LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES;
    """
    cursor.execute(query)
    cx.commit()

    final = time.time()
    print("cv_op importado con éxito (staging).")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")


def revisar_cv_op(cursor: Cursor) -> None:
    print("Revisando cv_op...")

    u = """
        SELECT t.ugen
        FROM (SELECT DISTINCT ugen FROM importar.cv_op) t
        LEFT JOIN importar.unidadgen2 u2 ON u2.central = t.ugen
        LEFT JOIN balance.unidadgeneracion u ON u.Nombre = u2.central_unidadgeneracion
        WHERE u.id IS NULL;
    """
    cursor.execute(u)
    revu = cursor.fetchall()

    if revu:
        print("REVISAR UNIDAD GENERACIÓN CV_OP!")
        input("Presione ENTER para continuar...")


def cargar_op(
    cx: Connection,
    cursor: Cursor,
    do_commit: bool = False,
) -> None:
    """
    PART2 (final): inserta en balance.cv_op.
    NO hace commit: el main decide commit/rollback.
    """
    print("Cargando cv_op (final)...")
    ini = time.time()

    carga = """
        INSERT INTO balance.cv_op
        SELECT
            v.id,
            hm.id,
            u.id,
            t.e_max,
            t.energia,
            t.cv,
            t.cvc,
            t.cvnc,
            t.cmedmt,
            t.costocombust,
            t.unidadcombust,
            t.tiempopartida,
            t.partidafriac,
            t.partidafriat,
            t.partidatibiac,
            t.partidatibiat,
            t.partidatibia2c,
            t.partidatibia2t,
            t.partidacalientec,
            t.partidacalientet,
            t.costodetencion
        FROM importar.cv_op t
        LEFT JOIN balance.`version` v
            ON v.periodo = t.periodo
           AND v.tipo    = 'DEFINITIVO'
        LEFT JOIN balance.hora_mensual hm
            ON hm.idversion = v.id
           AND hm.dia       = t.dia
           AND hm.hora      = 1
           AND hm.minuto    = 0
        LEFT JOIN importar.unidadgen2 u2
            ON u2.central = t.ugen
        LEFT JOIN balance.unidadgeneracion u
            ON u.Nombre = u2.central_unidadgeneracion;
    """
    cursor.execute(carga)

    if not do_commit:
        print("⚠️  cargar_op ejecutado en modo DRY (sin commit; lo decide el main).")

    final = time.time()
    print("cv_op: INSERT ejecutado.")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")