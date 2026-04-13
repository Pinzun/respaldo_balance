from .._locale import MESES_ES
# scripts/vertimiento.py
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from pymysql.connections import Connection
from pymysql.cursors import Cursor

from actualiza_balance.src.core.preflight_utils import PreflightItem, make_result

def preflight_reducciones(fecha: str, mode: str = "strict"):
    ruta_raw, ruta_processed, periodo = _rutas_reducciones(fecha)

    date = pd.to_datetime(fecha, yearfirst=True)
    año = date.year
    mes = date.month
    nombre_mes = MESES_ES[date.month]

    # armamos el nombre esperado según tu lógica (misma que procesar_reducciones)
    if año >= 2025:
        in_file = ruta_raw / (
            f"Reducciones-de-Energia-Eolica-Solar-Hidro-en-el-SEN_{nombre_mes}-{str(año)[-2:]}-PE-PFV.xlsx"
        )
    elif fecha in ("2024-12-01", "2024-11-01"):
        in_file = ruta_raw / (
            f"Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_{nombre_mes}-{str(año)[-2:]}-PE-PFV.xlsx"
        )
    elif datetime(2024, 6, 1) < date < datetime(2024, 11, 1):
        in_file = ruta_raw / (
            f"Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_{nombre_mes}-{str(año)[-2:]}-PE-PFV-HE.xlsx"
        )
    else:
        in_file = ruta_raw / (
            f"Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_{nombre_mes}-{str(año)[-2:]}.xlsx"
        )

    out_csv = ruta_processed / f"Vertimiento_{periodo}.csv"

    items = [
        PreflightItem("Reducciones raw dir", ruta_raw, True),
        PreflightItem("Reducciones input xlsx", in_file, True),
        PreflightItem("Reducciones processed dir (se crea)", ruta_processed, False),
        PreflightItem("Vertimiento csv (se genera)", out_csv, False),
    ]
    return make_result("reducciones/vertimiento", items, mode=mode)


def _rutas_reducciones(fecha: str) -> tuple[Path, Path, str]:
    """Devuelve (ruta_descarga_raw, ruta_carga_processed, periodo_YYMM)."""
    date = pd.to_datetime(fecha, yearfirst=True)
    año = date.year
    numero_mes = date.month
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent
    ruta_raw = ruta_base / "data" / "raw" / "reducciones"
    ruta_processed = ruta_base / "data" / "processed" / "reducciones"

    return ruta_raw, ruta_processed, periodo


def procesar_reducciones(fecha: str, tipo: str = "Definitivo") -> None:
    """Procesa los archivos de reducciones (vertimientos) y deja CSV en processed/reducciones."""

    ruta_descarga, ruta_carga, periodo = _rutas_reducciones(fecha)
    os.makedirs(ruta_carga, exist_ok=True)

    date = pd.to_datetime(fecha, yearfirst=True)
    año = date.year
    numero_mes = date.month
    nombre_mes = MESES_ES[date.month]

    if año >= 2025:
        nombre_archivo = (
            f"Reducciones-de-Energia-Eolica-Solar-Hidro-en-el-SEN_"
            f"{nombre_mes}-{str(año)[-2:]}-PE-PFV.xlsx"
        )
        hojas = {
            "Resumen-DiarioHorario-Eólico": "Eólico",
            "Resumen-DiarioHorario-Solar": "Solar",
            "Resumen-DiarioHorario-HP": "HP",
            "Resumen-DiarioHorario-HE": "HE",
        }
    elif fecha in ("2024-12-01", "2024-11-01"):
        nombre_archivo = (
            f"Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_"
            f"{nombre_mes}-{str(año)[-2:]}-PE-PFV.xlsx"
        )
        hojas = {
            "Resumen-DiarioHorario-Eólico": "Eólico",
            "Resumen-DiarioHorario-Solar": "Solar",
            "Resumen-DiarioHorario-HP": "HP",
            "Resumen-DiarioHorario-HE": "HE",
        }
    elif datetime(2024, 6, 1) < date < datetime(2024, 11, 1):
        nombre_archivo = (
            f"Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_"
            f"{nombre_mes}-{str(año)[-2:]}-PE-PFV-HE.xlsx"
        )
        hojas = {
            "Resumen-DiarioHorario-Eólico": "Eólico",
            "Resumen-DiarioHorario-Solar": "Solar",
            "Resumen-DiarioHorario-HP": "HP",
            "Resumen-DiarioHorario-HE": "HE",
        }
    else:
        nombre_archivo = (
            f"Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_"
            f"{nombre_mes}-{str(año)[-2:]}.xlsx"
        )
        hojas = {
            "Resumen-DiarioHorario-Eólico": "Eólico",
            "Resumen-DiarioHorario-Solar": "Solar",
        }

    archivo_xlsx = ruta_descarga / nombre_archivo
    if not archivo_xlsx.exists():
        raise FileNotFoundError(f"No existe archivo de reducciones: {archivo_xlsx}")

    vertimiento = []
    print(f"Procesando reducciones de {nombre_mes} {año}...")
    inicio = time.time()

    for hoja, tipo2 in hojas.items():
        print(f"Leyendo hoja {hoja}...")
        df = pd.read_excel(
            archivo_xlsx,
            sheet_name=hoja,
            header=None,
        )

        inicios = df[df[1] == "Central/Hora"].index.tolist()

        for inicio_idx in inicios:
            fin_idx = df.loc[inicio_idx:].loc[df[1] == "Total"].index[0]

            fecha_idx = inicio_idx - 2
            fecha_str = df.at[fecha_idx, 1]

            if fecha_str == "-" or pd.isna(fecha_str):
                continue

            fecha_dia = pd.to_datetime(fecha_str, dayfirst=True, errors="coerce")
            if pd.isna(fecha_dia) or fecha_dia.month != numero_mes:
                continue

            subtabla = df.loc[inicio_idx + 1 : fin_idx - 1, [1] + list(range(4, 28))].copy()
            subtabla.columns = ["Central"] + list(range(1, 25))

            subtabla = subtabla.melt(id_vars="Central", var_name="Hora", value_name="kwh")
            subtabla["Fecha"] = fecha_dia
            subtabla["Tipo"] = tipo2

            vertimiento.append(subtabla)

    if not vertimiento:
        print("No se encontraron subtables válidas. Revisa formato del archivo/hojas.")
        return

    vertimiento_final = pd.concat(vertimiento, ignore_index=True)
    nombre_archivo_fin = f"Vertimiento_{periodo}.csv"

    salida = (ruta_carga / nombre_archivo_fin).resolve()
    vertimiento_final.to_csv(
        salida,
        index=False,
        sep=",",
        decimal=".",
        encoding="utf-8",
    )

    fin = time.time()
    print(f"Proceso terminado.\nArchivo guardado en: {salida}")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(fin - inicio))}.")


def importar_vertimiento(cx: Connection, cursor: Cursor, fecha: str) -> None:
    """
    PART1 (staging): carga processed -> importar_.vertimiento.
    Aquí SÍ hacemos commit.
    """
    _, ruta_carga, periodo = _rutas_reducciones(fecha)
    ruta_vertimiento = (ruta_carga / f"Vertimiento_{periodo}.csv").resolve()

    if not ruta_vertimiento.exists():
        raise FileNotFoundError(f"Falta CSV de vertimiento para importar: {ruta_vertimiento}")

    cursor.execute("TRUNCATE TABLE importar_.vertimiento;")

    query = f"""
        LOAD DATA LOCAL INFILE '{str(ruta_vertimiento)}'
        INTO TABLE importar_.vertimiento
        CHARACTER SET UTF8MB4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
        LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES;
    """
    cursor.execute(query)
    cx.commit()


def revisar_vertimiento(cursor: Cursor) -> None:
    print("Revisando vertimiento...")

    revision = """
        SELECT t.central
        FROM (SELECT DISTINCT central FROM importar_.vertimiento) t
        LEFT JOIN importar_.unidadgen2 u2 ON u2.central = t.central
        LEFT JOIN balance.unidadgeneracion u ON u.Nombre = u2.central_unidadgeneracion
        WHERE u.id IS NULL;
    """
    cursor.execute(revision)
    rev = cursor.fetchall()

    if rev:
        print("REVISAR UGEN VERTIMIENTO!")
        input("Presione ENTER para continuar...")


def cargar_vertimientos(
    cx: Connection,
    cursor: Cursor,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """
    PART2 (final): inserta en balance.vertimiento.
    NO hace commit: el main decide commit/rollback.
    """
    carga = f"""
        INSERT INTO balance.vertimiento
        SELECT
            v.id,
            u.id,
            hm.id,
            t.kwh,
            t.tipo
        FROM importar_.vertimiento t
        LEFT JOIN balance.`version` v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        LEFT JOIN balance.hora_mensual hm
            ON hm.idversion = v.id
           AND hm.dia       = DAY(t.fecha)
           AND hm.hora      = t.hora
           AND hm.minuto    = 0
        LEFT JOIN importar_.unidadgen2 u2
            ON u2.central = t.central
        LEFT JOIN balance.unidadgeneracion u
            ON u.Nombre = u2.central_unidadgeneracion;
    """
    cursor.execute(carga)

    if not do_commit:
        print("⚠️  cargar_vertimientos ejecutado en modo DRY (sin commit; lo decide el main).")