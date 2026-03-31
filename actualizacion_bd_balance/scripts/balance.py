# scripts/balance.py
import os
import time
from pathlib import Path

import pandas as pd
from pymysql.connections import Connection
from pymysql.cursors import Cursor

from scripts.preflight_utils import PreflightItem, make_result, repo_root

def preflight_balance(fecha: str, tipo: str = "Definitivo", mode: str = "strict"):
    date = pd.to_datetime(fecha)
    año = date.year
    mes = date.month
    periodo = f"{str(año)[-2:]}{mes:02d}"
    version = tipo[0].capitalize()  # D/P

    root = repo_root()
    raw_dir = root / "data" / "raw" / "energia" / str(año) / periodo
    processed_dir = root / "data" / "processed" / "energia" / str(año) / periodo

    # inputs raw (los 5 originales)
    raw_files = [
        raw_dir / "Medidas_Valorizadas_15min_Norte.csv",
        raw_dir / "Medidas_Valorizadas_15min_Sur.csv",
        raw_dir / "Medidas_Valorizadas_15min_Norte Distribución.csv",
        raw_dir / "Medidas_Valorizadas_15min_Sur Distribución.csv",
        raw_dir / "Medidas_Valorizadas_15min_Compraventas.csv",
    ]

    # outputs processed esperados (los 4 que usa importar_balance)
    processed_files = [
        processed_dir / f"{periodo}_{version}_VALORIZADO_NORTE.csv",
        processed_dir / f"{periodo}_{version}_VALORIZADO_SUR.csv",
        processed_dir / f"{periodo}_{version}_VALORIZADO_NORTE_Dx.csv",
        processed_dir / f"{periodo}_{version}_VALORIZADO_SUR_Dx.csv",
        # contratos sale acá también, pero lo importa contratos.py
        processed_dir / f"{periodo}_{version}_contratos.csv",
    ]

    items = [PreflightItem("Balance raw dir", raw_dir, True)]
    items += [PreflightItem(f"Raw: {p.name}", p, True) for p in raw_files]
    items += [PreflightItem("Balance processed dir (se crea)", processed_dir, False)]
    # si vas a correr importar_balance sin correr procesar_medidas, estos serían requeridos.
    items += [PreflightItem(f"Processed (se genera): {p.name}", p, False) for p in processed_files]

    return make_result("balance", items, mode=mode)

def procesar_medidas(fecha: str, tipo: str = "Definitivo") -> None:
    """Procesa medidas valorizadas (archivos PLABACOM) y deja CSVs en /data/processed."""
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"
    version = tipo[0].capitalize()

    ruta_base = Path(__file__).resolve().parent.parent
    ruta_raw = ruta_base / "data" / "raw"
    ruta_processed = ruta_base / "data" / "processed"
    processed_dir = ruta_raw / "energia" / f"{año}" / f"{periodo}"
    raw_dir = ruta_processed / "energia" / f"{año}" / f"{periodo}"

    root = repo_root()
    raw_dir = root / "data" / "raw" / "energia" / str(año) / periodo
    processed_dir = root / "data" / "processed" / "energia" / str(año) / periodo


    archivos = {
        "Medidas_Valorizadas_15min_Norte.csv": f"{periodo}_{version}_VALORIZADO_NORTE.csv",
        "Medidas_Valorizadas_15min_Sur.csv": f"{periodo}_{version}_VALORIZADO_SUR.csv",
        "Medidas_Valorizadas_15min_Norte Distribución.csv": f"{periodo}_{version}_VALORIZADO_NORTE_Dx.csv",
        "Medidas_Valorizadas_15min_Sur Distribución.csv": f"{periodo}_{version}_VALORIZADO_SUR_Dx.csv",
        "Medidas_Valorizadas_15min_Compraventas.csv": f"{periodo}_{version}_contratos.csv",
    }

    encodings = ["utf-8", "latin1", "cp1252"]
    inicio = time.time()

    os.makedirs(raw_dir, exist_ok=True)

    for archivo, archivo_salida in archivos.items():
        print(f"Procesando archivo: {archivo}")

        df = None
        for encoding in encodings:
            try:
                df = pd.read_csv(
                    raw_dir / archivo,
                    parse_dates=["Fecha_Medicion"],
                    sep=";",
                    encoding=encoding,
                )
                break
            except UnicodeDecodeError:
                continue

        if df is None:
            print(f"⚠️  No se pudo leer {archivo} con ninguno de los encodings.")
            continue

        if archivo == "Medidas_Valorizadas_15min_Compraventas.csv":
            columnas = [
                "nombre_barra",
                "tension",
                "clave",
                "nro_lt",
                "Cuarto de Hora",
                "Fecha_Medicion",
                "Razon_Social",
                "RUT",
                "Nombre_Corto",
                "descripcion",
                "ID_Contrato",
                "tipo",
                "Precio",
                "Zona",
                "medida_1",
                "medida_2",
                "medida_3",
                "CMg[CLP/KWh]",
                "valorizado_CLP",
            ]
        else:
            columnas = [
                "nombre_barra",
                "tension",
                "clave",
                "nro_lt",
                "Cuarto de Hora",
                "Fecha_Medicion",
                "Razon_Social",
                "RUT",
                "Nombre_Corto",
                "descripcion",
                "ID_Contrato",
                "tipo",
                "Precio",
                "Zona",
                "medida_1",
                "medida_2",
                "medida_2a",
                "medida_3",
                "CMg[CLP/KWh]",
                "valorizado_CLP",
            ]

        df["RUT"] = df["RUT"].astype(str).str.replace(".", "", regex=False)
        balance = df[columnas].copy()
        del df

        balance.to_csv(
            processed_dir / archivo_salida,
            index=False,
            encoding="utf-8",
            sep=",",
            decimal=".",
        )
        del balance

    final = time.time()
    print(f"Archivos guardados en: {processed_dir}")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")


def importar_balance(
    cx: Connection,
    cursor: Cursor,
    fecha: str,
    tipo: str = "Definitivo",
) -> None:
    """PART1: Carga CSVs procesados a staging importar.balance (se permite commit)."""
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = date.month_name(locale="es_CL.utf8")
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"
    version = tipo[0].capitalize()



    ruta_base = Path(__file__).resolve().parent.parent
    ruta_processed = ruta_base / "data" / "processed" / "energia" / f"{año}" / f"{periodo}"

    f_norte = (ruta_processed / f"{periodo}_{version}_VALORIZADO_NORTE.csv").resolve()
    f_norte_dx = (ruta_processed / f"{periodo}_{version}_VALORIZADO_NORTE_Dx.csv").resolve()
    f_sur = (ruta_processed / f"{periodo}_{version}_VALORIZADO_SUR.csv").resolve()
    f_sur_dx = (ruta_processed / f"{periodo}_{version}_VALORIZADO_SUR_Dx.csv").resolve()


    print(f"Importando balance (staging) {nombre_mes} {año}...")
    inicio = time.time()

    # 1. Crear tabla si no existe
    create_table_query = """ 
    CREATE TABLE IF NOT EXISTS importar.balance (
        nombre_barra       VARCHAR(100),
        tension            INT,
        clave              VARCHAR(255),
        nro_lt             VARCHAR(50),
        `Cuarto de Hora`   INT,
        Fecha_Medicion     DATETIME,
        Razon_Social       VARCHAR(255),
        RUT                VARCHAR(20),
        Nombre_Corto       VARCHAR(100),
        descripcion        VARCHAR(255),
        ID_Contrato        VARCHAR(50),
        tipo               VARCHAR(50),
        Precio             VARCHAR(50),
        Zona               VARCHAR(100),
        medida_1           DECIMAL(25,5),
        medida_2           DECIMAL(25,5),
        medida_2a          DECIMAL(25,5),
        medida_3           DECIMAL(25,5),
        `CMg[CLP/KWh]`     DECIMAL(20,5),
        valorizado_CLP     DECIMAL(20,5)
    ) CHARACTER SET utf8mb4;

    """
    cursor.execute(create_table_query)

    cursor.execute("TRUNCATE TABLE importar.balance;")

    for f in (f_norte, f_norte_dx, f_sur, f_sur_dx):
        archivo_csv_str = str(f).replace("\\", "/")
        q = f"""
            LOAD DATA LOCAL INFILE '{archivo_csv_str}'
            INTO TABLE importar.balance
            CHARACTER SET UTF8MB4
            FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
            LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES;
        """
        cursor.execute(q)

    cx.commit()  # staging OK

    final = time.time()
    print("Balance (staging) importado con éxito.")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")


def revisar_balance(cursor: Cursor) -> None:
    print("Revisando datos balance (staging)...")

    # OJO: si barra_info es por versión, esta revisión sin idVersion puede dar falsos positivos/negativos.
    # La dejamos como "sanity check" básico.
    barras = """
        SELECT t.nombre_barra, t.tension
        FROM (SELECT DISTINCT nombre_barra, tension FROM importar.balance) t
        LEFT JOIN balance.barra_info b
            ON b.nombre = t.nombre_barra
           AND b.tension = t.tension
        WHERE b.idBarra IS NULL;
    """
    cursor.execute(barras)
    revb = cursor.fetchall()
    if revb:
        print("REVISAR BARRAS BALANCE!")
        input("Presione ENTER para continuar...")

    emp = """
        SELECT t.rut, t.nombre_corto
        FROM (SELECT DISTINCT rut, nombre_corto FROM importar.balance) t
        LEFT JOIN balance.empresa e ON e.id = t.rut
        WHERE e.id IS NULL;
    """
    cursor.execute(emp)
    reve = cursor.fetchall()
    if reve:
        print("REVISAR EMPRESAS BALANCE!")
        input("Presione ENTER para continuar...")

    des = """
        SELECT t.descripcion, t.tipo
        FROM (SELECT DISTINCT descripcion, tipo FROM importar.balance) t
        LEFT JOIN importar.descripcion2 d2 ON d2.col_8 = t.descripcion
        LEFT JOIN balance.descripcion d ON d.descripcion = d2.descripcion
        WHERE d.id IS NULL;
    """
    cursor.execute(des)
    revd = cursor.fetchall()
    if revd:
        print("REVISAR DESCRIPCIONES BALANCE!")
        input("Presione ENTER para continuar...")


def cargar_balance(
    cx: Connection,
    cursor: Cursor,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """
    PART2: Carga definitiva a balance.* (NO hace commit).
    El commit/rollback lo controla el main.
    """
    date = pd.to_datetime(fecha)
    año = date.year
    nombre_mes = date.month_name(locale="es_CL.utf8")
    tipo_db = tipo.upper()

    print(f"Cargando balance {nombre_mes} {año} (tipo={tipo_db})...")
    inicio = time.time()

    # 1) Empresas: OK que sea parte de la transacción PART2
    emp = """
        INSERT INTO balance.empresa (id, nombre)
        SELECT DISTINCT b.rut, b.nombre_corto
        FROM importar.balance b
        LEFT JOIN balance.empresa e ON e.id = b.rut
        WHERE e.id IS NULL;
    """
    cursor.execute(emp)

    # 2) Relación: amarrar barra_info a LA MISMA versión
    rel = f"""
        INSERT IGNORE INTO balance.relacion
            (idVersion, clave, idBarra, nro_lt, idEmpresa, idDescripcion, tipo1, zona, idContrato, precio)
        SELECT
            v.id,
            t.clave,
            bi.idBarra,
            t.nro_lt,
            t.rut,
            d.id,
            t.tipo,
            t.zona,
            t.id_contrato,
            t.precio
        FROM (
            SELECT DISTINCT
                nombre_barra, tension, clave, nro_lt,
                descripcion, id_contrato, zona, precio, rut, tipo
            FROM importar.balance
        ) t
        JOIN balance.`version` v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo_db}'
        JOIN balance.barra_info bi
            ON bi.idVersion = v.id
           AND bi.nombre    = t.nombre_barra
           AND bi.tension   = t.tension
        LEFT JOIN importar.descripcion2 d2
            ON d2.col_8 = t.descripcion
        LEFT JOIN balance.descripcion d
            ON d.descripcion = d2.descripcion;
    """
    cursor.execute(rel)

    # 3) Generación / retiro / transmisión: ojo con tipo_db (NO capitalize)
    gen = f"""
        INSERT IGNORE INTO balance.generacion
            (idVersion, clave, cuarto_hora, medidaHoraria2, medidahoraria, cmg_peso_kwh, valorizado_pesos)
        SELECT DISTINCT
            v.id,
            t.clave,
            t.cuarto_hora,
            t.medida_2,
            t.medida_1,
            t.cmg_pesos_kwh,
            t.valorizado_pesos
        FROM importar.balance t
        JOIN balance.`version` v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo_db}'
        WHERE t.tipo IN ('G', 'G_SAE', 'G_SAET');
    """
    cursor.execute(gen)

    ret = f"""
        INSERT IGNORE INTO balance.retiro
            (idVersion, clave, cuarto_hora, medidaHoraria2, medidahoraria, cmg_peso_kwh, valorizado_pesos)
        SELECT DISTINCT
            v.id,
            t.clave,
            t.cuarto_hora,
            t.medida_2,
            t.medida_1,
            t.cmg_pesos_kwh,
            t.valorizado_pesos
        FROM importar.balance t
        JOIN balance.`version` v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo_db}'
        WHERE t.tipo IN ('L', 'L_D', 'R');
    """
    cursor.execute(ret)

    trans = f"""
        INSERT IGNORE INTO balance.transmision
            (idVersion, clave, cuarto_hora, medidaHoraria2, medidahoraria, cmg_peso_kwh, valorizado_pesos)
        SELECT DISTINCT
            v.id,
            t.clave,
            t.cuarto_hora,
            t.medida_2,
            t.medida_1,
            t.cmg_pesos_kwh,
            t.valorizado_pesos
        FROM importar.balance t
        JOIN balance.`version` v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo_db}'
        WHERE t.tipo = 'T';
    """
    cursor.execute(trans)

    # ❗ NO commit aquí
    if not do_commit:
        print("⚠️  cargar_balance ejecutado en modo DRY (sin commit; lo decide el main).")

    final = time.time()
    print("Balance cargado (pendiente commit/rollback del main).")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")