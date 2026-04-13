from .._locale import MESES_ES
# factor_retiro_regulado_pg.py — versión PostgreSQL de factor_retiro_regulado.py
import time
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd


def preflight_frr(fecha: str, mode: str = "strict"):
    from actualiza_balance.src.core.mariaDB.factor_retiro_regulado import preflight_frr as _pf
    return _pf(fecha, mode)


def procesar_frr(fecha: str) -> None:
    from actualiza_balance.src.core.mariaDB.factor_retiro_regulado import procesar_frr as _pf
    return _pf(fecha)


def importar_frr(cx: Any, cursor: Any, fecha: str) -> None:
    """PART1 (staging): TRUNCATE + COPY a importar_mcp.retiroregulado [PostgreSQL]."""
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = MESES_ES[date.month]
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent.parent
    ruta_processed = ruta_base / "data" / "processed" / "energia" / str(año) / periodo
    archivo_csv = ruta_processed / f"retiroregulado_{periodo}.csv"

    if not archivo_csv.exists():
        raise FileNotFoundError(f"No existe el CSV de retiro regulado esperado: {archivo_csv}")

    print(f"Importando Retiro Regulado {nombre_mes} {año} (staging) [PostgreSQL]...")
    inicio = time.time()

    cursor.execute("TRUNCATE TABLE importar_mcp.retiroregulado;")

    # Columnas en el CSV (nombres del Excel) → columnas en la tabla staging
    col_csv = [
        "Bloque Regulado", "Suministrador",
        "kWh Punto Suministro", "%",
        "kWh Punto Suministro2", "%2",
        "Físico [kWh]", "Monetario [$]",
    ]
    col_tabla = [
        "bloque_regulado", "suministrador",
        "kwh_ps1", '"%_ps1"',
        "kwh_ps2", '"%_ps2"',
        "fisico_kwh", "monetario",
    ]
    col_tabla_plain = [
        "bloque_regulado", "suministrador",
        "kwh_ps1", "%_ps1",
        "kwh_ps2", "%_ps2",
        "fisico_kwh", "monetario",
    ]

    df = pd.read_csv(archivo_csv)
    if list(df.columns[:8]) != col_csv:
        # Intento de mapeo por posición si los nombres difieren
        df = df.iloc[:, :8]
    df.columns = col_tabla_plain

    buf = StringIO()
    df.to_csv(buf, index=False, header=True)
    buf.seek(0)
    # Las columnas con % requieren comillas dobles en PostgreSQL
    cols_str = ', '.join(f'"{c}"' if c.startswith('%') else c for c in col_tabla_plain)
    cursor.copy_expert(
        f'COPY importar_mcp.retiroregulado ({cols_str}) '
        "FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ',')",
        buf,
    )
    cx.commit()

    final = time.time()
    print("Retiro Regulado importado con éxito (staging) [PostgreSQL].")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")


def revisar_frr(cursor: Any) -> None:
    print("Revisando datos Retiro Regulado [PostgreSQL]...")

    query = """
        SELECT t.bloque_regulado
        FROM (SELECT DISTINCT bloque_regulado FROM importar_mcp.retiroregulado) t
        LEFT JOIN importar_mcp.empresa2 e2 ON e2.col_7 = t.bloque_regulado
        LEFT JOIN mercado_corto_plazo.empresa e ON e.nombre = e2.nombreempresa
        WHERE e.id IS NULL;
    """
    cursor.execute(query)
    rev1 = cursor.fetchall()
    if rev1:
        print("REVISAR BLOQUE REGULADO")
        input("Presione ENTER para continuar...")

    query1 = """
        SELECT t.suministrador
        FROM (SELECT DISTINCT suministrador FROM importar_mcp.retiroregulado) t
        LEFT JOIN importar_mcp.empresa2 e2 ON e2.col_7 = t.suministrador
        LEFT JOIN mercado_corto_plazo.empresa e ON e.nombre = e2.nombreempresa
        WHERE e.id IS NULL;
    """
    cursor.execute(query1)
    rev2 = cursor.fetchall()
    if rev2:
        print("REVISAR SUMINISTRADORES")
        input("Presione ENTER para continuar...")


def cargar_frr(
    cx: Any,
    cursor: Any,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """PART2 (final): inserta en mercado_corto_plazo.retiro_regulado [PostgreSQL]. NO hace commit."""
    date = pd.to_datetime(fecha)
    nombre_mes = MESES_ES[date.month]
    año = date.year

    print(f"Cargando Retiro Regulado {nombre_mes} {año} (final) [PostgreSQL]...")
    inicio = time.time()

    query = f"""
        INSERT INTO mercado_corto_plazo.retiro_regulado
        SELECT
            v.id,
            e.id,
            e2.id,
            r.kwh_ps1,
            r."%_ps1",
            r.kwh_ps2,
            r."%_ps2",
            r.fisico_kwh,
            r.monetario
        FROM importar_mcp.retiroregulado r
        JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        JOIN importar_mcp.empresa2 e3
            ON e3.col_7 = r.bloque_regulado
        JOIN mercado_corto_plazo.empresa e
            ON e.nombre = e3.nombreempresa
        JOIN importar_mcp.empresa2 e4
            ON e4.col_7 = r.suministrador
        JOIN mercado_corto_plazo.empresa e2
            ON e2.nombre = e4.nombreempresa
        ON CONFLICT DO NOTHING;
    """
    cursor.execute(query)

    if not do_commit:
        print("⚠️  cargar_frr ejecutado en modo DRY (sin commit; lo decide el main) [PostgreSQL].")

    final = time.time()
    print("Retiro Regulado: INSERT ejecutado [PostgreSQL].")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")
