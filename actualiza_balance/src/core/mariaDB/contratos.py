# scripts/contratos.py
import time
from pathlib import Path

import pandas as pd
from pymysql.connections import Connection
from pymysql.cursors import Cursor

from actualiza_balance.src.core.preflight_utils import PreflightItem, make_result, repo_root

def preflight_contratos(fecha: str, tipo: str = "Definitivo", mode: str = "strict"):
    date = pd.to_datetime(fecha)
    año = date.year
    mes = date.month
    periodo = f"{str(año)[-2:]}{mes:02d}"
    version = tipo[0].capitalize()

    root = repo_root()
    processed_dir = root / "data" / "processed" / "energia" / str(año) / periodo
    csv_file = processed_dir / f"{periodo}_{version}_contratos.csv"

    items = [
        PreflightItem("Contratos processed dir", processed_dir, must_exist=True),
        PreflightItem("Contratos csv output file (se generará)", csv_file, must_exist=False),
    ]
    return make_result("contratos", items, mode=mode)

def _ruta_contratos_csv(fecha: str, tipo: str) -> Path:
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"
    version = tipo[0].capitalize()  # D / P

    ruta_base = Path(__file__).resolve().parent.parent.parent
    ruta_processed = ruta_base / "data" / "processed"
    return (ruta_processed / "energia" / str(año) / periodo / f"{periodo}_{version}_contratos.csv").resolve()


def importar_contratos(
    cx: Connection,
    cursor: Cursor,
    fecha: str,
    tipo: str = "Definitivo",
) -> None:
    """
    PART1 (staging): TRUNCATE + LOAD a importar.contratos.
    Aquí SÍ hacemos commit, porque es staging (re-cargable).
    """
    print("Importando contratos (staging)...")
    ini = time.time()

    ruta_csv = _ruta_contratos_csv(fecha, tipo)
    if not ruta_csv.exists():
        raise FileNotFoundError(f"No existe el CSV de contratos esperado: {ruta_csv}")
    archivo_csv_str = str(ruta_csv).replace("\\", "/")
    
    # Truncar tabla (estructura definida en crea_importar.sql)
    cursor.execute("TRUNCATE TABLE importar.contratos;")

    query = f"""
        LOAD DATA LOCAL INFILE '{archivo_csv_str}'
        INTO TABLE importar.contratos
        CHARACTER SET UTF8MB4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
        LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES;
    """
    cursor.execute(query)
    cx.commit()

    final = time.time()
    print("Contratos importados con éxito (staging).")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")


def revisar_contratos(cursor: Cursor) -> None:
    print("Revisando contratos...")
    ini = time.time()

    barras = """
        SELECT t.nombre_barra, t.tension
        FROM (SELECT DISTINCT nombre_barra, tension FROM importar.contratos) t
        LEFT JOIN balance.barra_info b
            ON b.nombre  = t.nombre_barra
           AND b.tension = t.tension
        WHERE b.idBarra IS NULL;
    """
    cursor.execute(barras)
    revb = cursor.fetchall()
    if revb:
        print("REVISAR BARRAS CONTRATOS!")
        input("Presione ENTER para continuar...")

    emp = """
        SELECT t.rut, t.nombre_corto
        FROM (SELECT DISTINCT rut, nombre_corto FROM importar.contratos) t
        LEFT JOIN balance.empresa e ON e.id = t.rut
        WHERE e.id IS NULL;
    """
    cursor.execute(emp)
    reve = cursor.fetchall()
    if reve:
        print("REVISAR EMPRESAS CONTRATOS!")
        input("Presione ENTER para continuar...")

    final = time.time()
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")


def cargar_contratos(
    cx: Connection,
    cursor: Cursor,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """
    PART2 (final): inserta en tablas finales.
    NO hace commit. El main decide commit/rollback.
    """
    print("Cargando contratos (final)...")
    ini = time.time()

    # 1) Asegura que las empresas existan en balance.empresa (desde importar.contratos)
    query_emp = """
        INSERT IGNORE INTO balance.empresa (id, nombre)
        SELECT DISTINCT c.rut, c.nombre_corto
        FROM importar.contratos c
        LEFT JOIN balance.empresa e ON e.id = c.rut
        WHERE e.id IS NULL;
    """
    cursor.execute(query_emp)

    # 2) C_FIN info
    fin_info = f"""
        INSERT IGNORE INTO balance.c_fin_info
        SELECT
            v.id,
            c.id_contrato,
            c.descripcion,
            c.clave,
            e.id,
            b.idbarra,
            CASE
                WHEN LEFT(c.clave, 2) = 'V_' THEN 'VENTA'
                WHEN LEFT(c.clave, 2) = 'C_' THEN 'COMPRA'
                ELSE 'Otro'
            END AS transaccion
        FROM (
            SELECT DISTINCT
                nombre_barra,
                tension,
                clave,
                rut,
                descripcion,
                id_contrato
            FROM importar.contratos
            WHERE tipo = 'C_FIN'
        ) c
        JOIN balance.`version` v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        JOIN balance.empresa e
            ON e.id = c.rut
        JOIN balance.barra_info b
            ON b.idVersion = v.id
           AND b.nombre    = c.nombre_barra
           AND b.tension   = c.tension;
    """
    cursor.execute(fin_info)

    # 3) C_FIN med
    fin_med = f"""
        INSERT IGNORE INTO balance.c_fin_med
        SELECT
            v.id,
            c.clave,
            c.cuarto_hora,
            c.medida_1,
            c.cmg_peso_kwh,
            c.valorizado_pesos
        FROM importar.contratos c
        JOIN balance.`version` v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        WHERE c.tipo = 'C_FIN';
    """
    cursor.execute(fin_med)

    # 4) C_FIS info
    fis_info = f"""
        INSERT IGNORE INTO balance.c_fis_info
        SELECT
            v.id,
            c.id_contrato,
            c.descripcion,
            c.clave,
            e.id,
            b.idbarra,
            CASE
                WHEN LEFT(c.clave, 2) = 'V_' THEN 'VENTA'
                WHEN LEFT(c.clave, 2) = 'C_' THEN 'COMPRA'
                ELSE 'Otro'
            END AS transaccion
        FROM (
            SELECT DISTINCT
                nombre_barra,
                tension,
                clave,
                rut,
                descripcion,
                id_contrato
            FROM importar.contratos
            WHERE tipo = 'C_FIS'
        ) c
        JOIN balance.`version` v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        JOIN balance.empresa e
            ON e.id = c.rut
        JOIN balance.barra_info b
            ON b.idVersion = v.id
           AND b.nombre    = c.nombre_barra
           AND b.tension   = c.tension;
    """
    cursor.execute(fis_info)

    # 5) C_FIS med
    fis_med = f"""
        INSERT IGNORE INTO balance.c_fis_med
        SELECT
            v.id,
            c.clave,
            c.cuarto_hora,
            c.medida_1,
            c.cmg_peso_kwh,
            c.valorizado_pesos
        FROM importar.contratos c
        JOIN balance.`version` v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        WHERE c.tipo = 'C_FIS';
    """
    cursor.execute(fis_med)

    if not do_commit:
        print("⚠️  cargar_contratos ejecutado en modo DRY (sin commit; lo decide el main).")

    final = time.time()
    print("Contratos: INSERTs ejecutados.")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")