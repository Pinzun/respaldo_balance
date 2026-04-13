# contratos_pg.py — versión PostgreSQL de contratos.py
import time
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd


def preflight_contratos(fecha: str, tipo: str = "Definitivo", mode: str = "strict"):
    from actualiza_balance.src.core.mariaDB.contratos import preflight_contratos as _pf
    return _pf(fecha, tipo, mode)


def _ruta_contratos_csv(fecha: str, tipo: str) -> Path:
    from actualiza_balance.src.core.mariaDB.contratos import _ruta_contratos_csv as _r
    return _r(fecha, tipo)


def importar_contratos(
    cx: Any,
    cursor: Any,
    fecha: str,
    tipo: str = "Definitivo",
) -> None:
    """PART1 (staging): TRUNCATE + COPY a importar_mcp.contratos [PostgreSQL]."""
    print("Importando contratos (staging) [PostgreSQL]...")
    ini = time.time()

    ruta_csv = _ruta_contratos_csv(fecha, tipo)
    if not ruta_csv.exists():
        raise FileNotFoundError(f"No existe el CSV de contratos esperado: {ruta_csv}")

    cursor.execute("TRUNCATE TABLE importar_mcp.contratos;")

    col_csv = [
        "nombre_barra", "tension", "clave", "RUT", "Nombre_Corto",
        "descripcion", "ID_Contrato", "tipo", "Cuarto de Hora",
        "medida_1", "CMg[CLP/KWh]", "valorizado_CLP",
    ]
    col_tabla = [
        "nombre_barra", "tension", "clave", "rut", "nombre_corto",
        "descripcion", "id_contrato", "tipo", "cuarto_hora",
        "medida_1", "cmg_peso_kwh", "valorizado_pesos",
    ]

    df = pd.read_csv(ruta_csv, usecols=col_csv)
    df.columns = col_tabla

    buf = StringIO()
    df.to_csv(buf, index=False, header=True)
    buf.seek(0)
    cursor.copy_expert(
        f"COPY importar_mcp.contratos ({', '.join(col_tabla)}) "
        "FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ',')",
        buf,
    )
    cx.commit()

    final = time.time()
    print("Contratos importados con éxito (staging) [PostgreSQL].")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")


def revisar_contratos(cursor: Any) -> None:
    print("Revisando contratos [PostgreSQL]...")
    ini = time.time()

    barras = """
        SELECT t.nombre_barra, t.tension
        FROM (SELECT DISTINCT nombre_barra, tension FROM importar_mcp.contratos) t
        LEFT JOIN mercado_corto_plazo.barra_info b
            ON b.nombre  = t.nombre_barra
           AND b.tension = t.tension
        WHERE b."idBarra" IS NULL;
    """
    cursor.execute(barras)
    revb = cursor.fetchall()
    if revb:
        print("REVISAR BARRAS CONTRATOS!")
        input("Presione ENTER para continuar...")

    emp = """
        SELECT t.rut, t.nombre_corto
        FROM (SELECT DISTINCT rut, nombre_corto FROM importar_mcp.contratos) t
        LEFT JOIN mercado_corto_plazo.empresa e ON e.id = t.rut
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
    cx: Any,
    cursor: Any,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """PART2 (final): inserta en tablas finales [PostgreSQL]. NO hace commit."""
    print("Cargando contratos (final) [PostgreSQL]...")
    ini = time.time()

    # 1) Empresas
    query_emp = """
        INSERT INTO mercado_corto_plazo.empresa (id, nombre)
        SELECT DISTINCT c.rut, c.nombre_corto
        FROM importar_mcp.contratos c
        LEFT JOIN mercado_corto_plazo.empresa e ON e.id = c.rut
        WHERE e.id IS NULL;
    """
    cursor.execute(query_emp)

    # 2) C_FIN info
    fin_info = f"""
        INSERT INTO mercado_corto_plazo.c_fin_info
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
            SELECT DISTINCT nombre_barra, tension, clave, rut, descripcion, id_contrato
            FROM importar_mcp.contratos
            WHERE tipo = 'C_FIN'
        ) c
        JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        JOIN mercado_corto_plazo.empresa e ON e.id = c.rut
        JOIN mercado_corto_plazo.barra_info b
            ON b."idVersion" = v.id
           AND b.nombre       = c.nombre_barra
           AND b.tension      = c.tension
        ON CONFLICT DO NOTHING;
    """
    cursor.execute(fin_info)

    # 3) C_FIN med
    fin_med = f"""
        INSERT INTO mercado_corto_plazo.c_fin_med
        SELECT
            v.id,
            c.clave,
            c.cuarto_hora,
            c.medida_1,
            c.cmg_peso_kwh,
            c.valorizado_pesos
        FROM importar_mcp.contratos c
        JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        WHERE c.tipo = 'C_FIN'
        ON CONFLICT DO NOTHING;
    """
    cursor.execute(fin_med)

    # 4) C_FIS info
    fis_info = f"""
        INSERT INTO mercado_corto_plazo.c_fis_info
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
            SELECT DISTINCT nombre_barra, tension, clave, rut, descripcion, id_contrato
            FROM importar_mcp.contratos
            WHERE tipo = 'C_FIS'
        ) c
        JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        JOIN mercado_corto_plazo.empresa e ON e.id = c.rut
        JOIN mercado_corto_plazo.barra_info b
            ON b."idVersion" = v.id
           AND b.nombre       = c.nombre_barra
           AND b.tension      = c.tension
        ON CONFLICT DO NOTHING;
    """
    cursor.execute(fis_info)

    # 5) C_FIS med
    fis_med = f"""
        INSERT INTO mercado_corto_plazo.c_fis_med
        SELECT
            v.id,
            c.clave,
            c.cuarto_hora,
            c.medida_1,
            c.cmg_peso_kwh,
            c.valorizado_pesos
        FROM importar_mcp.contratos c
        JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        WHERE c.tipo = 'C_FIS'
        ON CONFLICT DO NOTHING;
    """
    cursor.execute(fis_med)

    if not do_commit:
        print("⚠️  cargar_contratos ejecutado en modo DRY (sin commit; lo decide el main) [PostgreSQL].")

    final = time.time()
    print("Contratos: INSERTs ejecutados [PostgreSQL].")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")
