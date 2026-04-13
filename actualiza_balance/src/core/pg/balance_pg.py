from .._locale import MESES_ES
# balance_pg.py — versión PostgreSQL de mercado_corto_plazo.py
import time
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd

from actualiza_balance.src.core.preflight_utils import PreflightItem, make_result, repo_root


def preflight_balance(fecha: str, tipo: str = "Definitivo", mode: str = "strict"):
    # Reutiliza la misma lógica de preflight (sin SQL)
    from actualiza_balance.src.core.mariaDB.balance import preflight_balance as _pf
    return _pf(fecha, tipo, mode)


def procesar_medidas(fecha: str, tipo: str = "Definitivo") -> None:
    # Sin SQL: reutiliza la función MySQL tal cual
    from actualiza_balance.src.core.mariaDB.balance import procesar_medidas as _pm
    return _pm(fecha, tipo)


def importar_balance(
    cx: Any,
    cursor: Any,
    fecha: str,
    tipo: str = "Definitivo",
) -> None:
    """PART1: Carga CSVs procesados a staging importar_mcp.balance (PostgreSQL)."""
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = MESES_ES[date.month]
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"
    version = tipo[0].capitalize()

    ruta_base = Path(__file__).resolve().parent.parent.parent
    ruta_processed = ruta_base / "data" / "processed" / "energia" / f"{año}" / f"{periodo}"

    archivos = [
        ruta_processed / f"{periodo}_{version}_VALORIZADO_NORTE.csv",
        ruta_processed / f"{periodo}_{version}_VALORIZADO_NORTE_Dx.csv",
        ruta_processed / f"{periodo}_{version}_VALORIZADO_SUR.csv",
        ruta_processed / f"{periodo}_{version}_VALORIZADO_SUR_Dx.csv",
    ]

    print(f"Importando balance (staging) {nombre_mes} {año} [PostgreSQL]...")
    inicio = time.time()

    cursor.execute("TRUNCATE TABLE importar_mcp.balance;")

    columnas = [
        "nombre_barra", "tension", "clave", "nro_lt", "Cuarto de Hora",
        "Fecha_Medicion", "RUT", "Nombre_Corto", "descripcion", "ID_Contrato",
        "tipo", "Precio", "Zona", "medida_1", "medida_2", "CMg[CLP/KWh]", "valorizado_CLP",
    ]
    col_tabla = [
        "nombre_barra", "tension", "clave", "nro_lt", "cuarto_hora",
        "fecha_medicion", "rut", "nombre_corto", "descripcion", "id_contrato",
        "tipo", "precio", "zona", "medida_1", "medida_2", "cmg_pesos_kwh", "valorizado_pesos",
    ]

    for f in archivos:
        df = pd.read_csv(f, usecols=columnas)
        buf = StringIO()
        df.to_csv(buf, index=False, header=True)
        buf.seek(0)
        cursor.copy_expert(
            f"COPY importar_mcp.balance ({', '.join(col_tabla)}) "
            "FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ',')",
            buf,
        )

    cx.commit()
    final = time.time()
    print("Balance (staging) importado con éxito [PostgreSQL].")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")


def revisar_balance(cursor: Any) -> None:
    print("Revisando datos balance (staging) [PostgreSQL]...")

    barras = """
        SELECT t.nombre_barra, t.tension
        FROM (SELECT DISTINCT nombre_barra, tension FROM importar_mcp.balance) t
        LEFT JOIN mercado_corto_plazo.barra_info b
            ON b.nombre = t.nombre_barra
           AND b.tension = t.tension
        WHERE b."idBarra" IS NULL;
    """
    cursor.execute(barras)
    revb = cursor.fetchall()
    if revb:
        print("REVISAR BARRAS BALANCE!")
        input("Presione ENTER para continuar...")

    emp = """
        SELECT t.rut, t.nombre_corto
        FROM (SELECT DISTINCT rut, nombre_corto FROM importar_mcp.balance) t
        LEFT JOIN mercado_corto_plazo.empresa e ON e.id = t.rut
        WHERE e.id IS NULL;
    """
    cursor.execute(emp)
    reve = cursor.fetchall()
    if reve:
        print("REVISAR EMPRESAS BALANCE!")
        input("Presione ENTER para continuar...")

    des = """
        SELECT t.descripcion, t.tipo
        FROM (SELECT DISTINCT descripcion, tipo FROM importar_mcp.balance) t
        LEFT JOIN importar_mcp.descripcion2 d2 ON d2.col_8 = t.descripcion
        LEFT JOIN mercado_corto_plazo.descripcion d ON d.descripcion = d2.descripcion
        WHERE d.id IS NULL;
    """
    cursor.execute(des)
    revd = cursor.fetchall()
    if revd:
        print("REVISAR DESCRIPCIONES BALANCE!")
        input("Presione ENTER para continuar...")


def cargar_balance(
    cx: Any,
    cursor: Any,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """PART2: Carga definitiva a mercado_corto_plazo.* (PostgreSQL). NO hace commit."""
    date = pd.to_datetime(fecha)
    año = date.year
    nombre_mes = MESES_ES[date.month]
    tipo_db = tipo.upper()

    print(f"Cargando balance {nombre_mes} {año} (tipo={tipo_db}) [PostgreSQL]...")
    inicio = time.time()

    # 1) Empresas
    emp = """
        INSERT INTO mercado_corto_plazo.empresa (id, nombre)
        SELECT DISTINCT b.rut, b.nombre_corto
        FROM importar_mcp.balance b
        LEFT JOIN mercado_corto_plazo.empresa e ON e.id = b.rut
        WHERE e.id IS NULL;
    """
    cursor.execute(emp)

    # 2) Relación
    rel = f"""
        INSERT INTO mercado_corto_plazo.relacion
            ("idVersion", clave, "idBarra", nro_lt, "idEmpresa", "idDescripcion", tipo1, zona, "idContrato", precio)
        SELECT
            v.id,
            t.clave,
            bi."idBarra",
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
            FROM importar_mcp.balance
        ) t
        JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo_db}'
        JOIN mercado_corto_plazo.barra_info bi
            ON bi."idVersion" = v.id
           AND bi.nombre       = t.nombre_barra
           AND bi.tension      = t.tension
        LEFT JOIN importar_mcp.descripcion2 d2
            ON d2.col_8 = t.descripcion
        LEFT JOIN mercado_corto_plazo.descripcion d
            ON d.descripcion = d2.descripcion
        ON CONFLICT DO NOTHING;
    """
    cursor.execute(rel)

    # 3) Generación
    gen = f"""
        INSERT INTO mercado_corto_plazo.generacion
            ("idVersion", clave, cuarto_hora, "medidaHoraria2", medidahoraria, cmg_peso_kwh, valorizado_pesos)
        SELECT DISTINCT
            v.id,
            t.clave,
            t.cuarto_hora,
            t.medida_2,
            t.medida_1,
            t.cmg_pesos_kwh,
            t.valorizado_pesos
        FROM importar_mcp.balance t
        JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo_db}'
        WHERE t.tipo IN ('G', 'G_SAE', 'G_SAET')
        ON CONFLICT DO NOTHING;
    """
    cursor.execute(gen)

    # 4) Retiro
    ret = f"""
        INSERT INTO mercado_corto_plazo.retiro
            ("idVersion", clave, cuarto_hora, "medidaHoraria2", medidahoraria, cmg_peso_kwh, valorizado_pesos)
        SELECT DISTINCT
            v.id,
            t.clave,
            t.cuarto_hora,
            t.medida_2,
            t.medida_1,
            t.cmg_pesos_kwh,
            t.valorizado_pesos
        FROM importar_mcp.balance t
        JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo_db}'
        WHERE t.tipo IN ('L', 'L_D', 'R')
        ON CONFLICT DO NOTHING;
    """
    cursor.execute(ret)

    # 5) Transmisión
    trans = f"""
        INSERT INTO mercado_corto_plazo.transmision
            ("idVersion", clave, cuarto_hora, "medidaHoraria2", medidahoraria, cmg_peso_kwh, valorizado_pesos)
        SELECT DISTINCT
            v.id,
            t.clave,
            t.cuarto_hora,
            t.medida_2,
            t.medida_1,
            t.cmg_pesos_kwh,
            t.valorizado_pesos
        FROM importar_mcp.balance t
        JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo_db}'
        WHERE t.tipo = 'T'
        ON CONFLICT DO NOTHING;
    """
    cursor.execute(trans)

    if not do_commit:
        print("⚠️  cargar_balance ejecutado en modo DRY (sin commit; lo decide el main) [PostgreSQL].")

    final = time.time()
    print("Balance cargado (pendiente commit/rollback del main) [PostgreSQL].")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")
