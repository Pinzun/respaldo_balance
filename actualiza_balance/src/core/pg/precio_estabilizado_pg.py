from .._locale import MESES_ES
# precio_estabilizado_pg.py — versión PostgreSQL de precio_estabilizado.py
import time
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd


def preflight_precio_estabilizado(fecha: str, tipo: str = "Definitivo", mode: str = "strict"):
    from actualiza_balance.src.core.mariaDB.precio_estabilizado import preflight_precio_estabilizado as _pf
    return _pf(fecha, tipo, mode)


def _paths(fecha: str):
    from actualiza_balance.src.core.mariaDB.precio_estabilizado import _paths as _p
    return _p(fecha)


def procesar_compensacion(fecha: str, tipo: str = "Definitivo") -> None:
    from actualiza_balance.src.core.mariaDB.precio_estabilizado import procesar_compensacion as _pc
    return _pc(fecha, tipo)


def procesar_inyecciones(fecha: str, tipo: str = "Definitivo") -> None:
    from actualiza_balance.src.core.mariaDB.precio_estabilizado import procesar_inyecciones as _pi
    return _pi(fecha, tipo)


def importar_pe(cx: Any, cursor: Any, fecha: str) -> None:
    """PART1 (staging): TRUNCATE + COPY a importar_mcp.compensacion e importar_mcp.inyecciones [PostgreSQL]."""
    año, _, periodo, _, ruta_carga = _paths(fecha)
    nombre_mes = MESES_ES[pd.to_datetime(fecha).month]

    print(f"Importando precio estabilizado {año} {nombre_mes} (staging) [PostgreSQL]...")
    ini = time.time()

    comp_csv = ruta_carga / f"{periodo}_compensacion.csv"
    iny_norte_csv = ruta_carga / f"{periodo}_inyecciones_norte.csv"
    iny_sur_csv = ruta_carga / f"{periodo}_inyecciones_sur.csv"

    for p in (comp_csv, iny_norte_csv, iny_sur_csv):
        if not p.exists():
            raise FileNotFoundError(f"Falta archivo requerido PE: {p}")

    # Compensación
    cursor.execute("TRUNCATE TABLE importar_mcp.compensacion;")
    col_comp = ["hora_mensual", "suministrador", "prorrata_suministrador",
                "diferencia_horaria", "compensacion"]
    df_comp = pd.read_csv(comp_csv)
    df_comp = df_comp.iloc[:, :5]
    df_comp.columns = col_comp
    buf = StringIO()
    df_comp.to_csv(buf, index=False, header=True)
    buf.seek(0)
    cursor.copy_expert(
        f"COPY importar_mcp.compensacion ({', '.join(col_comp)}) "
        "FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ',')",
        buf,
    )

    # Inyecciones
    cursor.execute("TRUNCATE TABLE importar_mcp.inyecciones;")
    col_iny_csv = [
        "Cuarto de Hora", "clave", "RUT", "Nombre_Corto", "descripcion",
        "nombre_barra_cmg", "tipo", "precio_pncp", "medida_1",
        "CMG_PESO_KWH", "Valorizado_cmg", "Valorizado_pncp", "Diferencia_pncp-cmg",
    ]
    col_iny_tabla = [
        "cuarto_hora", "clave", "rut", "nombre_corto", "descripcion",
        "nombre_barra_cmg", "tipo", "precio_pncp", "medida_1",
        "cmg_peso_kwh", "valorizado_cmg", "valorizado_pncp", "diferencia_pncp_cmg",
    ]

    for iny_csv in (iny_norte_csv, iny_sur_csv):
        df_iny = pd.read_csv(iny_csv, usecols=col_iny_csv)
        df_iny.columns = col_iny_tabla
        buf2 = StringIO()
        df_iny.to_csv(buf2, index=False, header=True)
        buf2.seek(0)
        cursor.copy_expert(
            f"COPY importar_mcp.inyecciones ({', '.join(col_iny_tabla)}) "
            "FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ',')",
            buf2,
        )

    cx.commit()
    final = time.time()
    print("Precio estabilizado importado con éxito (staging) [PostgreSQL].")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")


def revisar_compensacion(cursor: Any) -> None:
    print("Revisando compensación [PostgreSQL]...")
    ini = time.time()

    emp = """
        SELECT t.suministrador
        FROM (SELECT DISTINCT suministrador FROM importar_mcp.compensacion) t
        LEFT JOIN importar_mcp.empresa2 e2 ON e2.col_7 = t.suministrador
        LEFT JOIN mercado_corto_plazo.empresa e ON e.nombre = e2.nombreempresa
        WHERE e.id IS NULL;
    """
    cursor.execute(emp)
    reve = cursor.fetchall()
    if reve:
        print("REVISAR EMPRESAS COMPENSACION!")
        input("Presione ENTER para continuar...")

    final = time.time()
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")


def revisar_inyecciones(cursor: Any, fecha: str, tipo: str = "Definitivo") -> None:
    print("Revisando inyecciones [PostgreSQL]...")

    emp = """
        SELECT t.rut
        FROM (SELECT DISTINCT rut FROM importar_mcp.inyecciones) t
        LEFT JOIN mercado_corto_plazo.empresa e ON e.id = t.rut
        WHERE e.id IS NULL;
    """
    cursor.execute(emp)
    reve = cursor.fetchall()
    if reve:
        print("REVISAR EMPRESAS INYECCIONES!")
        input("Presione ENTER para continuar...")

    bar = """
        SELECT t.nombre_barra_cmg
        FROM (SELECT DISTINCT nombre_barra_cmg FROM importar_mcp.inyecciones) t
        LEFT JOIN importar_mcp.barra2 b2 ON b2.col_1 = t.nombre_barra_cmg
        LEFT JOIN mercado_corto_plazo.barra b ON b.nombre = b2.nombrebarra
        WHERE b.id IS NULL;
    """
    cursor.execute(bar)
    revb = cursor.fetchall()
    if revb:
        print("REVISAR BARRAS INYECCIONES!")
        input("Presione ENTER para continuar...")

    rel = f"""
        SELECT
            i.clave,
            i.nombre_corto AS prop_iny,     e.nombre AS prop_rel,
            i.descripcion AS desc_iny,      d.descripcion AS desc_rel,
            i.nombre_barra_cmg AS barra_iny, b.nombre AS barra_rel,
            i.tipo AS tipo_iny,             r.tipo1 AS tipo_rel
        FROM (
            SELECT DISTINCT clave, rut, nombre_corto, descripcion, nombre_barra_cmg, tipo
            FROM importar_mcp.inyecciones
        ) i
        LEFT JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}' AND v.tipo = '{tipo.upper()}'
        JOIN mercado_corto_plazo.relacion r
            ON r.clave = i.clave AND r."idVersion" = v.id
        LEFT JOIN mercado_corto_plazo.empresa e ON e.id = i.rut
        LEFT JOIN importar_mcp.descripcion2 d2 ON d2.col_8 = i.descripcion
        LEFT JOIN mercado_corto_plazo.descripcion d ON d.id = r."idDescripcion"
        LEFT JOIN importar_mcp.barra2 b2 ON b2.col_1 = i.nombre_barra_cmg
        LEFT JOIN mercado_corto_plazo.barra b ON b.id = r."idBarra"
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
            i.medida_1 AS gen_iny,       g.medidahoraria AS gen_gen,
            i.cmg_peso_kwh AS cmg_iny,   g.cmg_peso_kwh AS cmg_gen
        FROM importar_mcp.inyecciones i
        LEFT JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}' AND v.tipo = '{tipo.upper()}'
        JOIN mercado_corto_plazo.generacion g
            ON g.clave = i.clave AND g."idVersion" = v.id AND g.cuarto_hora = i.cuarto_hora
        WHERE (
            ABS(i.medida_1 - g.medidahoraria) > 0.01 OR
            ABS(i.cmg_peso_kwh - g.cmg_peso_kwh) > 0.01
        );
    """
    cursor.execute(gen)
    revgen = cursor.fetchall()
    if revgen:
        print("REVISAR GENERACION INYECCIONES!")
        input("Presione ENTER para continuar...")


def cargar_compensacion(
    cx: Any,
    cursor: Any,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """PART2 (final): inserta en mercado_corto_plazo.pe_compensacion [PostgreSQL]. NO hace commit."""
    date = pd.to_datetime(fecha)
    año = date.year
    nombre_mes = MESES_ES[date.month]

    print(f"Cargando compensaciones {año} {nombre_mes} (final) [PostgreSQL]...")
    ini = time.time()

    carga = f"""
        INSERT INTO mercado_corto_plazo.pe_compensacion
            (idversion, hora_mensual, "idEmpresa", prorrata_suministrador, diferencia_horaria, compensacion)
        SELECT DISTINCT
            v.id,
            t.hora_mensual,
            e.id,
            t.prorrata_suministrador,
            t.diferencia_horaria,
            t.compensacion
        FROM importar_mcp.compensacion t
        LEFT JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}' AND v.tipo = '{tipo.upper()}'
        LEFT JOIN importar_mcp.empresa2 e2
            ON e2.col_7 = t.suministrador
        LEFT JOIN mercado_corto_plazo.empresa e
            ON e.nombre = e2.nombreempresa
        ON CONFLICT DO NOTHING;
    """
    cursor.execute(carga)

    if not do_commit:
        print("⚠️  cargar_compensacion ejecutado en modo DRY (sin commit; lo decide el main) [PostgreSQL].")

    final = time.time()
    print("Compensaciones: INSERT ejecutado [PostgreSQL].")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")


def cargar_inyecciones(
    cx: Any,
    cursor: Any,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """PART2 (final): inserta en mercado_corto_plazo.pe_inyecciones [PostgreSQL]. NO hace commit."""
    date = pd.to_datetime(fecha)
    año = date.year
    nombre_mes = MESES_ES[date.month]

    print(f"Cargando inyecciones {año} {nombre_mes} (final) [PostgreSQL]...")
    ini = time.time()

    carga = f"""
        INSERT INTO mercado_corto_plazo.pe_inyecciones
            ("idVersion", clave, cuarto_hora, precio_nudo, valorizado_pnudo, diferencia_pnudo_cmg, observacion)
        SELECT
            v.id,
            i.clave,
            i.cuarto_hora,
            i.precio_pncp,
            i.valorizado_pncp,
            i.diferencia_pncp_cmg,
            'Carga PE (controlada por commit externo)'
        FROM importar_mcp.inyecciones i
        LEFT JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}' AND v.tipo = '{tipo.upper()}'
        ON CONFLICT DO NOTHING;
    """
    cursor.execute(carga)

    if not do_commit:
        print("⚠️  cargar_inyecciones ejecutado en modo DRY (sin commit; lo decide el main) [PostgreSQL].")

    final = time.time()
    print("Inyecciones: INSERT ejecutado [PostgreSQL].")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")
