from .._locale import MESES_ES
# scripts/barras.py
import os
import time
import pandas as pd
from pymysql.connections import Connection
from pymysql.cursors import Cursor
from pathlib import Path

from actualiza_balance.src.core.preflight_utils import PreflightItem, make_result, repo_root

def preflight_barras(fecha: str, mode: str = "strict"):
    date = pd.to_datetime(fecha)
    año = date.year
    mes = date.month
    periodo = f"{str(año)[-2:]}{mes:02d}"

    root = repo_root()
    raw_dir = root / "data" / "raw" / "energia" / str(año) / periodo
    processed_dir = root / "data" / "processed" / "energia" / str(año) / periodo

    in_file = next(raw_dir.glob("Barras_export*.xlsx"))
    out_file = processed_dir / f"{periodo}_Barras.csv"

    items = [
        PreflightItem("Barras raw dir", raw_dir, True),
        PreflightItem("Barras input xlsx", in_file, True),
        PreflightItem("Barras processed dir (se crea)", processed_dir, False),
        PreflightItem("Barras output csv (se genera)", out_file, False),
    ]
    return make_result("barras", items, mode=mode)

def procesar_barras(fecha: str) -> None:
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    root = repo_root()
    raw_dir = root / "data" / "raw" / "energia" / str(año) / periodo
    processed_dir = root / "data" / "processed" / "energia" / str(año) / periodo
    os.makedirs(processed_dir, exist_ok=True)


    in_file = next(raw_dir.glob("Barras_export*.xlsx"))
    out_file = processed_dir / f"{periodo}_Barras.csv"


    print(f"Procesando archivo: {in_file}")
    inicio = time.time()

    df = pd.read_excel(
        in_file,
        sheet_name="data",
        usecols="A:K",
    )  


    df.to_csv(
        out_file,
        index=False,
        encoding="utf-8",
        sep=",",
        decimal=".",
    )
    del df

    final = time.time()
    print(f"Archivo guardado en: {out_file}")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")


def importar_barras(cx: Connection, cursor: Cursor, fecha: str) -> None:
    """
    PART1 (staging): carga a importar.barras_importadas.
    Aquí sí se permite commit (TRUNCATE + LOAD).
    """
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = MESES_ES[date.month]
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent
    ruta_processed = ruta_base / "data" / "processed" / "energia" / f"{año}" / f"{periodo}"
    archivo_csv = (ruta_processed / f"{periodo}_Barras.csv").resolve()
    # Normalizar la ruta para MySQL
    archivo_csv_str = str(archivo_csv).replace("\\", "/")

    print(f"Importando barras (staging) {nombre_mes} {año}...")
    inicio = time.time()

    # Truncar tabla (estructura definida en crea_importar.sql)
    cursor.execute("TRUNCATE TABLE importar.barras_importadas;")

    query = f"""
        LOAD DATA LOCAL INFILE '{archivo_csv_str}'
        INTO TABLE importar.barras_importadas
        CHARACTER SET UTF8MB4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
        LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES;
    """
    cursor.execute(query)
    cx.commit()  # staging OK

    final = time.time()
    print("Barras importadas con éxito.")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")


def revisar_barras_info(cursor: Cursor) -> None:
    print("Revisando empresas barras_importadas...")

    e = """
        SELECT t.empresa
        FROM (SELECT DISTINCT empresa FROM importar.barras_importadas) t
        LEFT JOIN importar.empresa2 e2 ON e2.col_7 = t.empresa
        LEFT JOIN balance.empresa e ON e.nombre = e2.nombreempresa
        WHERE e.id IS NULL;
    """
    cursor.execute(e)
    reve = cursor.fetchall()

    if reve:
        print("REVISAR EMPRESAS DE BARRAS IMPORTADAS!")
        input("Presione ENTER para continuar...")


def cargar_barras_info(
    cx: Connection,
    cursor: Cursor,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """
    PART2 (final): inserta en balance.barra_info.
    NO hace commit: el main decide commit/rollback.
    """
    date = pd.to_datetime(fecha)
    año = date.year
    nombre_mes = MESES_ES[date.month]
    tipo_db = tipo.upper()

    print(f"Cargando barras_importadas {año} {nombre_mes} (tipo={tipo_db})...")
    inicio = time.time()

    # OJO:
    # - uso JOIN con balance.version para no insertar con v.id NULL
    # - unifico tu bar/bar2 con COALESCE(b.id, 0)
    bar = f"""
        INSERT INTO balance.barra_info
            (idVersion, idBarra, nombre, tension, nombre_cmg, subestacion,
             idInfotecnica, codigo_cne, nombre_cne, comuna, calificacion,
             zona_concesion, zona_transicion)
        SELECT
            v.id,
            COALESCE(b.id, 0) AS idBarra,
            t.nombre_barra,
            t.tension,
            b2.nombrebarra,
            t.subestacion,
            t.barra_infotecnica,
            t.codigo_cne,
            t.nombre_barra_cne,
            t.comuna,
            t.calificacion,
            t.zona_concesion,
            t.zona_transicion
        FROM importar.barras_importadas t
        JOIN balance.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo_db}'
        LEFT JOIN (
            SELECT DISTINCT nombre_barra, tension, nombre_barra_cmg
            FROM importar.cmg
        ) cm
            ON cm.nombre_barra = t.nombre_barra
           AND cm.tension      = t.tension
        LEFT JOIN importar.barra2 b2
            ON b2.col_1 = cm.nombre_barra_cmg
        LEFT JOIN balance.barra b
            ON b.nombre = b2.nombrebarra;
    """
    cursor.execute(bar)

    if not do_commit:
        print("⚠️  cargar_barras_info ejecutado en modo DRY (sin commit; lo decide el main).")

    final = time.time()
    print("Barras_info insert ejecutado.")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")