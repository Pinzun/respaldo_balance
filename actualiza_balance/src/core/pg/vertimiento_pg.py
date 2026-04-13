# vertimiento_pg.py — versión PostgreSQL de vertimiento.py
import time
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd


def preflight_reducciones(fecha: str, mode: str = "strict"):
    from actualiza_balance.src.core.mariaDB.vertimiento import preflight_reducciones as _pf
    return _pf(fecha, mode)


def procesar_reducciones(fecha: str, tipo: str = "Definitivo") -> None:
    from actualiza_balance.src.core.mariaDB.vertimiento import procesar_reducciones as _pr
    return _pr(fecha, tipo)


def _rutas_reducciones(fecha: str):
    from actualiza_balance.src.core.mariaDB.vertimiento import _rutas_reducciones as _rr
    return _rr(fecha)


def importar_vertimiento(cx: Any, cursor: Any, fecha: str) -> None:
    """PART1 (staging): carga processed → importar_mcp.vertimiento [PostgreSQL]."""
    _, ruta_carga, periodo = _rutas_reducciones(fecha)
    ruta_vertimiento = ruta_carga / f"Vertimiento_{periodo}.csv"

    if not ruta_vertimiento.exists():
        raise FileNotFoundError(f"Falta CSV de vertimiento para importar: {ruta_vertimiento}")

    cursor.execute("TRUNCATE TABLE importar_mcp.vertimiento;")

    col_tabla = ["central", "hora", "kwh", "fecha", "tipo"]
    df = pd.read_csv(ruta_vertimiento)
    # Columnas esperadas: Central, Hora, kwh, Fecha, Tipo
    df = df.iloc[:, :5]
    df.columns = col_tabla

    buf = StringIO()
    df.to_csv(buf, index=False, header=True)
    buf.seek(0)
    cursor.copy_expert(
        f"COPY importar_mcp.vertimiento ({', '.join(col_tabla)}) "
        "FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ',')",
        buf,
    )
    cx.commit()


def revisar_vertimiento(cursor: Any) -> None:
    print("Revisando vertimiento [PostgreSQL]...")

    revision = """
        SELECT t.central
        FROM (SELECT DISTINCT central FROM importar_mcp.vertimiento) t
        LEFT JOIN importar_mcp.unidadgen2 u2 ON u2.central = t.central
        LEFT JOIN mercado_corto_plazo.unidadgeneracion u ON u."Nombre" = u2.central_unidadgeneracion
        WHERE u.id IS NULL;
    """
    cursor.execute(revision)
    rev = cursor.fetchall()
    if rev:
        print("REVISAR UGEN VERTIMIENTO!")
        input("Presione ENTER para continuar...")


def cargar_vertimientos(
    cx: Any,
    cursor: Any,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """PART2 (final): inserta en mercado_corto_plazo.vertimiento [PostgreSQL]. NO hace commit."""
    # DAY() → EXTRACT(DAY FROM ...)
    carga = f"""
        INSERT INTO mercado_corto_plazo.vertimiento
        SELECT
            v.id,
            u.id,
            hm.id,
            t.kwh,
            t.tipo
        FROM importar_mcp.vertimiento t
        LEFT JOIN mercado_corto_plazo.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        LEFT JOIN mercado_corto_plazo.hora_mensual hm
            ON hm.idversion = v.id
           AND hm.dia       = EXTRACT(DAY FROM t.fecha)
           AND hm.hora      = t.hora
           AND hm.minuto    = 0
        LEFT JOIN importar_mcp.unidadgen2 u2
            ON u2.central = t.central
        LEFT JOIN mercado_corto_plazo.unidadgeneracion u
            ON u."Nombre" = u2.central_unidadgeneracion;
    """
    cursor.execute(carga)

    if not do_commit:
        print("⚠️  cargar_vertimientos ejecutado en modo DRY (sin commit; lo decide el main) [PostgreSQL].")
