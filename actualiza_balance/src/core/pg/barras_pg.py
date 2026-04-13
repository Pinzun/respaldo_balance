from .._locale import MESES_ES
# barras_pg.py — versión PostgreSQL de barras.py
import time
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd


def preflight_barras(fecha: str, mode: str = "strict"):
    from actualiza_balance.src.core.mariaDB.barras import preflight_barras as _pf
    return _pf(fecha, mode)


def procesar_barras(fecha: str) -> None:
    from actualiza_balance.src.core.mariaDB.barras import procesar_barras as _pb
    return _pb(fecha)


def importar_barras(cx: Any, cursor: Any, fecha: str) -> None:
    """PART1 (staging): carga a importar_mcp.barras_importadas [PostgreSQL]."""
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = MESES_ES[date.month]
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent.parent
    ruta_processed = ruta_base / "data" / "processed" / "energia" / f"{año}" / f"{periodo}"
    archivo_csv = ruta_processed / f"{periodo}_Barras.csv"

    print(f"Importando barras (staging) {nombre_mes} {año} [PostgreSQL]...")
    inicio = time.time()

    cursor.execute("TRUNCATE TABLE importar_mcp.barras_importadas;")

    col_tabla = [
        "nombre_barra", "tension", "barra_infotecnica", "codigo_cne",
        "nombre_barra_cne", "subestacion", "comuna", "calificacion",
        "zona_concesion", "zona_transicion", "empresa",
    ]

    df = pd.read_csv(archivo_csv)
    # Renombrar columnas al nombre de la tabla staging si difieren
    df = df.iloc[:, :len(col_tabla)]
    df.columns = col_tabla

    df = df.iloc[:, :len(col_tabla)]
    df.columns = col_tabla

    # Convertir columnas enteras que vienen como float por NaN
    df["barra_infotecnica"] = pd.to_numeric(df["barra_infotecnica"], errors="coerce").astype("Int64")

    buf = StringIO()

    buf = StringIO()
    df.to_csv(buf, index=False, header=True)
    buf.seek(0)
    cursor.copy_expert(
        f"COPY importar_mcp.barras_importadas ({', '.join(col_tabla)}) "
        "FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ',')",
        buf,
    )
    cx.commit()

    final = time.time()
    print("Barras importadas con éxito [PostgreSQL].")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")


def revisar_barras_info(cursor: Any) -> None:
    print("Revisando empresas barras_importadas [PostgreSQL]...")

    e = """
        SELECT t.empresa
        FROM (SELECT DISTINCT empresa FROM importar_mcp.barras_importadas) t
        LEFT JOIN importar_mcp.empresa2 e2 ON e2.col_7 = t.empresa
        LEFT JOIN mercado_corto_plazo.empresa e ON e.nombre = e2.nombreempresa
        WHERE e.id IS NULL;
    """
    cursor.execute(e)
    reve = cursor.fetchall()

    if reve:
        print("REVISAR EMPRESAS DE BARRAS IMPORTADAS!")
        input("Presione ENTER para continuar...")


def cargar_barras_info(
    cx: Any,
    cursor: Any,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """PART2 (final): inserta en mercado_corto_plazo.barra_info [PostgreSQL]. NO hace commit."""
    date = pd.to_datetime(fecha)
    año = date.year
    nombre_mes = MESES_ES[date.month]
    tipo_db = tipo.upper()

    print(f"Cargando barras_importadas {año} {nombre_mes} (tipo={tipo_db}) [PostgreSQL]...")
    inicio = time.time()

    bar = f"""
        INSERT INTO mercado_corto_plazo.barra_info
            ("idVersion", "idBarra", nombre, tension, nombre_cmg, subestacion,
             "idInfotecnica", codigo_cne, nombre_cne, comuna, calificacion,
             zona_concesion, zona_transicion)
        SELECT
            v.id,
            COALESCE(b.id, 0) AS "idBarra",
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
        FROM importar_mcp.barras_importadas t
        JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo_db}'
        LEFT JOIN (
            SELECT DISTINCT nombre_barra, tension, nombre_barra_cmg
            FROM importar_mcp.cmg
        ) cm
            ON cm.nombre_barra = t.nombre_barra
           AND cm.tension      = t.tension
        LEFT JOIN importar_mcp.barra2 b2
            ON b2.col_1 = cm.nombre_barra_cmg
        LEFT JOIN mercado_corto_plazo.barra b
            ON b.nombre = b2.nombrebarra;
    """
    cursor.execute(bar)

    if not do_commit:
        print("⚠️  cargar_barras_info ejecutado en modo DRY (sin commit; lo decide el main) [PostgreSQL].")

    final = time.time()
    print("Barras_info insert ejecutado [PostgreSQL].")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")
