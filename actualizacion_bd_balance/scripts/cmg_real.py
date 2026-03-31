# scripts/cmg_real.py
import os
import time
from calendar import monthrange
from datetime import datetime
from pathlib import Path

import pandas as pd
from pymysql.connections import Connection
from pymysql.cursors import Cursor

from scripts.preflight_utils import PreflightItem, make_result, repo_root


def preflight_cmg_real(fecha: str, tipo: str = "Definitivo", mode: str = "skip"):
    dt = pd.to_datetime(fecha)
    año = dt.year
    mes = dt.month
    periodo = f"{str(año)[-2:]}{mes:02d}"

    root = repo_root()
    raw_dir = root / "data" / "raw" / "cmg_real" / str(año) / periodo
    processed_dir = root / "data" / "processed" / "cmg_real" / str(año) / periodo
    out_csv = processed_dir / f"{periodo}cmg_real.csv"

    daily_glob = "CMgxBarraMinuto_*.csv"

    # ✅ OJO: NO pasar raw_dir/daily_glob como Path "con asterisco" a PreflightItem.
    items = [
        PreflightItem("CMG_REAL raw dir", raw_dir, True),
        # ✅ Lo dejamos como item informativo (no requerido) o lo sacamos derechamente.
        PreflightItem(f"CMG_REAL daily files pattern: {daily_glob}", raw_dir, False),
        PreflightItem("CMG_REAL processed dir (se crea)", processed_dir, False),
        PreflightItem("CMG_REAL output csv (se genera)", out_csv, False),
    ]

    r = make_result("cmg_real", items, mode=mode)

    # --- validación real de archivos diarios ---
    daily_files = list(raw_dir.glob(daily_glob)) if raw_dir.exists() else []

    # Partimos de missing que ya detectó make_result (por ejemplo raw_dir no existe)
    missing = list(r.missing)

    # Quitamos cualquier “missing” raro del item de patrón si se imprimiera en otra capa
    missing = [it for it in missing if "daily files" not in it.label]

    if mode == "skip":
        # En skip: basta con >=1 archivo
        if raw_dir.exists() and not daily_files:
            missing.append(
                PreflightItem(
                    f"CMG_REAL daily files: {daily_glob} (se requiere al menos 1)",
                    raw_dir,
                    True,
                )
            )
    else:
        # En strict: exigir TODOS los días del mes
        _, dias = monthrange(año, mes)
        expected = [
            raw_dir / f"CMgxBarraMinuto_{año}{mes:02d}{d:02d}.csv"
            for d in range(1, dias + 1)
        ]
        missing_days = [p for p in expected if not p.exists()]
        if missing_days:
            missing.append(
                PreflightItem(
                    f"CMG_REAL missing daily file (ejemplo). Faltan {len(missing_days)} días",
                    missing_days[0],
                    True,
                )
            )

    r.missing = missing
    return r

def procesar_cmg_real(fecha: str) -> None:
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = date.month_name(locale="es_CL.utf8")
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent
    ruta_raw = ruta_base / "data" / "raw"
    ruta_processed = ruta_base / "data" / "processed"

    ruta_carpeta_descarga = ruta_raw / "cmg_real" / f"{año}" / f"{periodo}"
    ruta_carpeta_carga = ruta_processed / "cmg_real" / f"{año}" / f"{periodo}"

    os.makedirs(ruta_carpeta_carga, exist_ok=True)

    _, dias = monthrange(año, numero_mes)

    cmg_real = []
    print(f"Procesando CMgReal de {nombre_mes} {año}...")
    ini = time.time()

    for dia in range(1, dias + 1):
        cmg = f"CMgxBarraMinuto_{año}{numero_mes:02d}{dia:02d}.csv"
        path_cmg = ruta_carpeta_descarga / cmg

        df = pd.read_csv(path_cmg, sep=";")

        columnas = [
            "Fecha",
            "Hora",
            "Minuto",
            "SD",
            "Configuracion",
            "Barra",
            "CMg[USD/MWh]",
            "CMg[CLP/kWh]",
            "Tipo",
        ]

        # Archivos antiguos no traen 'Tipo'
        if int(periodo) < 2501:
            df["Tipo"] = ""

        df.columns = columnas
        df["dia"] = dia
        df["periodo"] = datetime(año, numero_mes, 1)

        df = df[
            [
                "periodo",
                "dia",
                "Hora",
                "Minuto",
                "SD",
                "Configuracion",
                "Barra",
                "CMg[USD/MWh]",
                "CMg[CLP/kWh]",
                "Tipo",
            ]
        ]

        cmg_real.append(df)

    cmg_real_final = pd.concat(cmg_real, ignore_index=True)

    salida = ruta_carpeta_carga / f"{periodo}cmg_real.csv"
    cmg_real_final.to_csv(
        salida,
        index=False,
        sep=",",
        decimal=".",
        encoding="utf-8",
    )

    fin = time.time()
    print(f"Archivo guardado en: {salida}")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(fin - ini))}.")


def importar_cmg_real(cx: Connection, cursor: Cursor, fecha: str) -> None:
    """
    PART1 (staging): TRUNCATE + LOAD a importar.cmg_real.
    Aquí sí se permite commit.
    """
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = date.month_name(locale="es_CL.utf8")
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent
    ruta_processed = ruta_base / "data" / "processed" / "cmg_real" / f"{año}" / f"{periodo}"
    archivo_csv = (ruta_processed / f"{periodo}cmg_real.csv").resolve()
    cmg_real_csv_str = str(archivo_csv).replace("\\", "/")

    print(f"Importando CMgReal (staging) de {nombre_mes} {año}...")
    ini = time.time()

    #Crear tabla importar.cmg_real si no existe
    create_table_query="""
    CREATE TABLE IF NOT EXISTS importar.cmg_real (
    periodo           DATE NOT NULL,
    dia               INT NOT NULL,
    hora              INT NOT NULL,
    minuto            INT NOT NULL,
    sistema_designado VARCHAR(50),
    configuracion     VARCHAR(255),
    barra             VARCHAR(255),
    cmg_usd_mwh       FLOAT,
    cmg_clp_kwh       FLOAT,
    tipo              VARCHAR(100)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;    
    """
    cursor.execute(create_table_query)

    cursor.execute("TRUNCATE TABLE importar.cmg_real;")

    query = f"""
        LOAD DATA LOCAL INFILE '{cmg_real_csv_str}'
        INTO TABLE importar.cmg_real
        CHARACTER SET UTF8MB4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
        LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES;
    """
    cursor.execute(query)
    cx.commit()  # staging OK

    fin = time.time()
    print("CMgReal importado con éxito.")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(fin - ini))}.")


def revisar_cmg_real(cursor: Cursor) -> None:
    """
    Revisión mínima coherente con el dataset:
    - valida que las barras existan en el maestro.
    (No reviso unidad_gen porque aquí no existe esa columna en cmg_real.)
    """
    print("Revisando cmg_real...")

    b = """
        SELECT t.barra
        FROM (SELECT DISTINCT Barra AS barra FROM importar.cmg_real) t
        LEFT JOIN importar.barra2 b2 ON b2.col_1 = t.barra
        LEFT JOIN balance.barra b ON b.nombre = b2.nombrebarra
        WHERE b.id IS NULL;
    """
    cursor.execute(b)
    revb = cursor.fetchall()
    if revb:
        print("REVISAR BARRAS CMG REAL!")
        input("Presione ENTER para continuar...")


def cargar_cmg_real(
    cx: Connection,
    cursor: Cursor,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """
    PART2 (final): inserta en balance.cmg_real.
    NO hace commit: lo decide el main.

    OJO: este INSERT asume que la tabla importar.cmg_real tiene las columnas
    exactamente como se cargan desde el CSV (periodo, dia, Hora, Minuto, SD,
    Configuracion, Barra, CMg[USD/MWh], CMg[CLP/kWh], Tipo).
    Si tu tabla staging usa otros nombres (snake_case), cámbialos aquí.
    """
    tipo_db = tipo.upper()
    print("Cargando cmg_real...")
    ini = time.time()

    carga = f"""
        INSERT INTO balance.cmg_real
            (idVersion, dia, hora, minuto, sd, configuracion, idBarra,
             cmg_usd_mwh, cmg_clp_kwh, tipo)
        SELECT
            v.id,
            t.dia,
            t.Hora,
            t.Minuto,
            t.SD,
            t.Configuracion,
            b.id,
            t.`CMg[USD/MWh]`,
            t.`CMg[CLP/kWh]`,
            t.Tipo
        FROM importar.cmg_real t
        JOIN balance.version v
            ON v.periodo = t.periodo
           AND v.tipo   = '{tipo_db}'
        LEFT JOIN importar.barra2 b2
            ON b2.col_1 = t.Barra
        LEFT JOIN balance.barra b
            ON b.nombre = b2.nombrebarra;
    """
    cursor.execute(carga)

    if not do_commit:
        print("⚠️  cargar_cmg_real ejecutado en modo DRY (sin commit; lo decide el main).")

    fin = time.time()
    print(f"Insert cmg_real ejecutado. Tiempo: {time.strftime('%H:%M:%S', time.gmtime(fin - ini))}.")