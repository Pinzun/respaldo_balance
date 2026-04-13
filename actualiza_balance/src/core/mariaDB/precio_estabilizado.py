from .._locale import MESES_ES
# scripts/precio_estabilizado.py
import os
import time
from pathlib import Path

import pandas as pd
from pymysql.connections import Connection
from pymysql.cursors import Cursor
from actualiza_balance.src.core.preflight_utils import PreflightItem, make_result, repo_root

def preflight_precio_estabilizado(fecha: str, tipo: str = "Definitivo", mode: str = "strict"):
    año, numero_mes, periodo, ruta_descarga, ruta_carga = _paths(fecha)
    version = tipo[0].capitalize()

    # compensación: nombre varía por año/periodo
    if (año < 2023) or (año == 2022 and numero_mes <= 12):
        comp_in = ruta_descarga / f"Precio_estabilizado_{periodo}.xlsb"
    else:
        comp_in = ruta_descarga / f"Reconstruye_valorizado_pnpc_pe_{periodo}{version}.xlsx"

    # inyecciones: 2 csv raw
    iny_norte_in = ruta_descarga / f"inyec_valorizadas_norte_{periodo}{version}.csv"
    iny_sur_in = ruta_descarga / f"inyec_valorizadas_sur_{periodo}{version}.csv"

    # outputs processed
    comp_out = ruta_carga / f"{periodo}_compensacion.csv"
    iny_norte_out = ruta_carga / f"{periodo}_inyecciones_norte.csv"
    iny_sur_out = ruta_carga / f"{periodo}_inyecciones_sur.csv"

    items = [
        PreflightItem("PE raw dir", ruta_descarga, True),
        PreflightItem("PE compensación input", comp_in, True),
        PreflightItem("PE iny norte input", iny_norte_in, True),
        PreflightItem("PE iny sur input", iny_sur_in, True),
        PreflightItem("PE processed dir (se crea)", ruta_carga, False),
        PreflightItem("PE compensación output (se genera)", comp_out, False),
        PreflightItem("PE iny norte output (se genera)", iny_norte_out, False),
        PreflightItem("PE iny sur output (se genera)", iny_sur_out, False),
    ]
    return make_result("precio_estabilizado", items, mode=mode)

def _paths(fecha: str) -> tuple[int, int, str, Path, Path]:
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent
    ruta_raw = ruta_base / "data" / "raw"
    ruta_processed = ruta_base / "data" / "processed"

    # Fuente PE (originales) y salida PE (csv procesados)
    ruta_descarga = ruta_raw / "energia" / str(año) / periodo
    ruta_carga = ruta_processed / "energia" / str(año) / periodo

    return año, numero_mes, periodo, ruta_descarga, ruta_carga


def procesar_compensacion(fecha: str, tipo: str = "Definitivo") -> None:
    date = pd.to_datetime(fecha)
    año, numero_mes, periodo, ruta_descarga, ruta_carga = _paths(fecha)
    version = tipo[0].capitalize()

    if (año < 2023) or (año == 2022 and numero_mes <= 12):
        archivo = f"Precio_estabilizado_{periodo}.xlsb"
    else:
        archivo = f"Reconstruye_valorizado_pnpc_pe_{periodo}{version}.xlsx"

    print(f"Procesando archivo (compensación): {archivo}")
    inicio = time.time()

    df = pd.read_excel(
        ruta_descarga / archivo,
        sheet_name="Compensación",
        usecols="A:E",
    )

    os.makedirs(ruta_carga, exist_ok=True)
    salida = (ruta_carga / f"{periodo}_compensacion.csv").resolve()

    df.to_csv(
        salida,
        index=False,
        encoding="utf-8",
        sep=",",
        decimal=".",
    )

    final = time.time()
    print(f"Archivo guardado en: {salida}")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")


def procesar_inyecciones(fecha: str, tipo: str = "Definitivo") -> None:
    año, _, periodo, ruta_descarga, ruta_carga = _paths(fecha)
    version = tipo[0].capitalize()

    archivos = {
        f"inyec_valorizadas_norte_{periodo}{version}.csv": f"{periodo}_inyecciones_norte.csv",
        f"inyec_valorizadas_sur_{periodo}{version}.csv": f"{periodo}_inyecciones_sur.csv",
    }

    print(f"Procesando inyecciones PE {periodo} ({año})...")
    inicio = time.time()

    os.makedirs(ruta_carga, exist_ok=True)

    columnas = [
        "Cuarto de Hora",
        "clave",
        "Razon_Social",
        "RUT",
        "Nombre_Corto",
        "descripcion",
        "nombre_barra_cmg",
        "tipo",
        "precio_pncp",
        "medida_1",
        "CMG_PESO_KWH",
        "Valorizado_cmg",
        "Valorizado_pncp",
        "Diferencia_pncp-cmg",
    ]

    for archivo_in, archivo_out in archivos.items():
        print(f"  - Leyendo: {archivo_in}")

        df = pd.read_csv(
            ruta_descarga / archivo_in,
            sep=";",
        )

        df["RUT"] = df["RUT"].astype(str).str.replace(".", "", regex=False)
        iny = df[columnas].copy()

        salida = (ruta_carga / archivo_out).resolve()
        iny.to_csv(
            salida,
            index=False,
            encoding="utf-8",
            sep=",",
            decimal=".",
        )

    final = time.time()
    print(f"Archivos guardados en: {ruta_carga}")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")


def importar_pe(cx: Connection, cursor: Cursor, fecha: str) -> None:
    """
    PART1 (staging): TRUNCATE + LOAD a importar.compensacion e importar.inyecciones.
    Aquí SÍ hacemos commit.
    """
    año, _, periodo, _, ruta_carga = _paths(fecha)
    nombre_mes = MESES_ES[pd.to_datetime(fecha).month]

    print(f"Importando precio estabilizado {año} {nombre_mes} (staging)...")
    ini = time.time()

    comp_csv = (ruta_carga / f"{periodo}_compensacion.csv").resolve()
    iny_norte_csv = (ruta_carga / f"{periodo}_inyecciones_norte.csv").resolve()
    iny_sur_csv = (ruta_carga / f"{periodo}_inyecciones_sur.csv").resolve()

    for p in (comp_csv, iny_norte_csv, iny_sur_csv):
        if not p.exists():
            raise FileNotFoundError(f"Falta archivo requerido PE: {p}")
        # Normalizar la ruta para MySQL
    comp_csv_str = str(comp_csv).replace("\\", "/")
    iny_norte_csv_str = str(iny_norte_csv).replace("\\", "/")
    iny_sur_csv_str = str(iny_sur_csv).replace("\\", "/")

    # Truncar tabla (estructura definida en crea_importar.sql)
    cursor.execute("TRUNCATE TABLE importar.compensacion;")
    q1 = f"""
        LOAD DATA LOCAL INFILE '{comp_csv_str}'
        INTO TABLE importar.compensacion
        CHARACTER SET UTF8MB4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
        LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES;
    """
    cursor.execute(q1)


    # Truncar tabla (estructura definida en crea_importar.sql)
    cursor.execute("TRUNCATE TABLE importar.inyecciones;")
    q2 = f"""
        LOAD DATA LOCAL INFILE '{iny_norte_csv_str}'
        INTO TABLE importar.inyecciones
        CHARACTER SET UTF8MB4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
        LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES;
    """
    cursor.execute(q2)

    q3 = f"""
        LOAD DATA LOCAL INFILE '{iny_sur_csv_str}'
        INTO TABLE importar.inyecciones
        CHARACTER SET UTF8MB4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
        LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES;
    """
    cursor.execute(q3)

    cx.commit()

    final = time.time()
    print("Precio estabilizado importado con éxito (staging).")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")


def revisar_compensacion(cursor: Cursor) -> None:
    print("Revisando compensación...")
    ini = time.time()

    emp = """
        SELECT t.suministrador
        FROM (SELECT DISTINCT suministrador FROM importar.compensacion) t
        LEFT JOIN importar.empresa2 e2 ON e2.col_7 = t.suministrador
        LEFT JOIN balance.empresa e ON e.nombre = e2.nombreempresa
        WHERE e.id IS NULL;
    """
    cursor.execute(emp)
    reve = cursor.fetchall()

    if reve:
        print("REVISAR EMPRESAS COMPENSACION!")
        input("Presione ENTER para continuar...")

    final = time.time()
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")


def revisar_inyecciones(cursor: Cursor, fecha: str, tipo: str = "Definitivo") -> None:
    print("Revisando inyecciones...")

    emp = """
        SELECT t.rut
        FROM (SELECT DISTINCT rut FROM importar.inyecciones) t
        LEFT JOIN balance.empresa e ON e.id = t.rut
        WHERE e.id IS NULL;
    """
    cursor.execute(emp)
    reve = cursor.fetchall()
    if reve:
        print("REVISAR EMPRESAS INYECCIONES!")
        input("Presione ENTER para continuar...")

    # OJO: aquí tu staging trae "nombre_barra_cmg" (según procesar_inyecciones),
    # pero tu query anterior revisaba "nombre_barra". Lo dejamos en CMG por consistencia.
    bar = """
        SELECT t.nombre_barra_cmg
        FROM (SELECT DISTINCT nombre_barra_cmg FROM importar.inyecciones) t
        LEFT JOIN importar.barra2 b2 ON b2.col_1 = t.nombre_barra_cmg
        LEFT JOIN balance.barra b ON b.nombre = b2.nombrebarra
        WHERE b.id IS NULL;
    """
    cursor.execute(bar)
    revb = cursor.fetchall()
    if revb:
        print("REVISAR BARRAS INYECCIONES!")
        input("Presione ENTER para continuar...")

    # Si quieres mantener tus chequeos de consistencia contra relacion/generacion,
    # los dejamos tal cual pero tipados con Cursor y tipo.upper().
    # (Puede fallar por nombres de columnas: perfecto para detectar en ejecución.)
    rel = f"""
        SELECT 
            i.clave,
            i.nombre_corto AS prop_iny,     e.nombre AS prop_rel,
            i.descripcion AS desc_iny,      d.descripcion AS desc_rel,
            i.nombre_barra_cmg AS barra_iny,    b.nombre AS barra_rel,
            i.tipo AS tipo_iny,             r.tipo1 AS tipo_rel
        FROM (
            SELECT DISTINCT clave, rut, nombre_corto, descripcion, nombre_barra_cmg, tipo
            FROM importar.inyecciones
        ) i
        LEFT JOIN balance.`version` v
            ON v.periodo = '{fecha}' AND v.tipo = '{tipo.upper()}'
        JOIN balance.relacion r
            ON r.clave = i.clave AND r.idVersion = v.id
        LEFT JOIN balance.empresa e
            ON e.id = i.rut
        LEFT JOIN importar.descripcion2 d2
            ON d2.col_8 = i.descripcion
        LEFT JOIN balance.descripcion d
            ON d.id = r.idDescripcion
        LEFT JOIN importar.barra2 b2
            ON b2.col_1 = i.nombre_barra_cmg
        LEFT JOIN balance.barra b
            ON b.id = r.idBarra
        WHERE (
            e.nombre <> i.nombre_corto OR
            d2.descripcion <> d.descripcion OR
            b2.nombrebarra <> b.nombre OR
            i.tipo <> r.tipo1
        );
    """
    cursor.execute(rel)
    revrel = cursor.fetchall()
    if revrel:
        print("REVISAR RELACION CLAVE INYECCIONES!")
        input("Presione ENTER para continuar...")

    gen = f"""
        SELECT
            i.clave, i.cuarto_hora,
            i.medida_1 AS gen_iny,      g.medidahoraria AS gen_gen,
            i.CMG_PESO_KWH AS cmg_iny,  g.cmg_peso_kwh AS cmg_gen
        FROM importar.inyecciones i
        LEFT JOIN balance.`version` v
            ON v.periodo = '{fecha}' AND v.tipo = '{tipo.upper()}'
        JOIN balance.generacion g
            ON g.clave = i.clave AND g.idVersion = v.id AND g.cuarto_hora = i.cuarto_hora
        WHERE (
            ABS(i.medida_1 - g.medidahoraria) > 0.01 OR
            ABS(i.CMG_PESO_KWH - g.cmg_peso_kwh) > 0.01
        );
    """
    cursor.execute(gen)
    revgen = cursor.fetchall()
    if revgen:
        print("REVISAR GENERACION INYECCIONES!")
        input("Presione ENTER para continuar...")


def cargar_compensacion(
    cx: Connection,
    cursor: Cursor,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """
    PART2 (final): inserta en balance.pe_compensacion.
    NO hace commit: el main decide commit/rollback.
    """
    date = pd.to_datetime(fecha)
    año = date.year
    nombre_mes = MESES_ES[date.month]

    print(f"Cargando compensaciones {año} {nombre_mes} (final)...")
    ini = time.time()

    carga = f"""
        INSERT IGNORE INTO balance.pe_compensacion
            (idversion, hora_mensual, idEmpresa, prorrata_suministrador, diferencia_horaria, compensacion)
        SELECT DISTINCT
            v.id,
            t.hora_mensual,
            e.id,
            t.prorrata_suministrador,
            t.diferencia_horaria,
            t.compensacion
        FROM importar.compensacion t
        LEFT JOIN balance.`version` v
            ON v.periodo = '{fecha}' AND v.tipo = '{tipo.upper()}'
        LEFT JOIN importar.empresa2 e2
            ON e2.col_7 = t.suministrador
        LEFT JOIN balance.empresa e
            ON e.nombre = e2.nombreempresa;
    """
    cursor.execute(carga)

    if not do_commit:
        print("⚠️  cargar_compensacion ejecutado en modo DRY (sin commit; lo decide el main).")

    final = time.time()
    print("Compensaciones: INSERT ejecutado.")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")


def cargar_inyecciones(
    cx: Connection,
    cursor: Cursor,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """
    PART2 (final): inserta en balance.pe_inyecciones.
    NO hace commit: el main decide commit/rollback.
    """
    date = pd.to_datetime(fecha)
    año = date.year
    nombre_mes = MESES_ES[date.month]

    print(f"Cargando inyecciones {año} {nombre_mes} (final)...")
    ini = time.time()

    carga = f"""
        INSERT IGNORE INTO balance.pe_inyecciones
            (idVersion, clave, cuarto_hora, precio_nudo, valorizado_pnudo, diferencia_pnudo_cmg, observacion)
        SELECT
            v.id,
            i.clave,
            i.cuarto_hora,
            i.precio_pncp,
            i.valorizado_pncp,
            i.diferencia_pncp_cmg,
            'Carga PE (controlada por commit externo)'
        FROM importar.inyecciones i
        LEFT JOIN balance.`version` v
            ON v.periodo = '{fecha}' AND v.tipo = '{tipo.upper()}';
    """
    cursor.execute(carga)

    if not do_commit:
        print("⚠️  cargar_inyecciones ejecutado en modo DRY (sin commit; lo decide el main).")

    final = time.time()
    print("Inyecciones: INSERT ejecutado.")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")