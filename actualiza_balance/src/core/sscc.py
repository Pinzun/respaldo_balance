# scripts/sscc.py
import os
import time
from pathlib import Path

import pandas as pd
from pymysql.connections import Connection
from pymysql.cursors import Cursor

from actualiza_balance.src.core.preflight_utils import PreflightItem, make_result, repo_root
import re


def _find_sscc_xlsm(raw_dir: Path, periodo: str, tipo: str) -> Path | None:
    """
    Busca el archivo SSCC .xlsm dentro de raw_dir de forma tolerante:
    - Acepta variaciones de mayúsculas/minúsculas.
    - Acepta que 'def' / 'pre' / etc aparezca como sufijo.
    - Prioriza match exacto esperado si existe.
    """
    if not raw_dir.exists():
        return None

    tipo3 = (tipo[:3] or "").lower()  # "def", "pre", etc.
    expected = f"1_CUADROS_PAGO_SSCC_{periodo}_{tipo3}.xlsm"
    exact = raw_dir / expected
    if exact.exists():
        return exact

    # patrón flexible
    # ejemplos válidos:
    # 1_CUADROS_PAGO_SSCC_2510_def.xlsm
    # 1_CUADROS_PAGO_SSCC_2510_DEF.xlsm
    # 1_CUADROS_PAGO_SSCC_2510_def_v2.xlsm (si existiera)
    pat = re.compile(
        rf"^1[_\-\s]*CUADROS[_\-\s]*PAGO[_\-\s]*SSCC[_\-\s]*{re.escape(periodo)}.*{re.escape(tipo3)}.*\.xlsm$",
        re.IGNORECASE,
    )

    candidates = [p for p in raw_dir.glob("*.xlsm") if pat.match(p.name)]
    if not candidates:
        return None

    # si hay varios, elige el más nuevo (mtime)
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def preflight_sscc(fecha: str, tipo: str = "Definitivo", mode: str = "strict"):
    dt = pd.to_datetime(fecha)
    año = dt.year
    mes = dt.month
    periodo = f"{str(año)[-2:]}{mes:02d}"

    root = repo_root()
    raw_dir = root / "data" / "raw" / "sscc" / str(año) / periodo
    processed_dir = root / "data" / "processed" / "sscc" / str(año) / periodo

    # Resolver input real en disco (robusto)
    resolved_in = _find_sscc_xlsm(raw_dir, periodo, tipo)

    # Para el log, dejamos "esperado" como referencia, pero el requerido será el resuelto
    tipo3 = (tipo[:3] or "").lower()
    expected_name = f"1_CUADROS_PAGO_SSCC_{periodo}_{tipo3}.xlsm"
    expected_path = raw_dir / expected_name

    # Si no se resolvió, usamos el expected_path para que el log muestre qué se esperaba
    in_file = resolved_in or expected_path

    rt_out = processed_dir / f"sscc_rt_{periodo}.csv"
    infra_out = processed_dir / f"sscc_infra_{periodo}.csv"
    emp_out = processed_dir / f"empresas_sscc_{periodo}.csv"

    items = [
        PreflightItem("SSCC raw dir", raw_dir, True),
        PreflightItem(f"SSCC input xlsm (esperado: {expected_name})", in_file, True),
        PreflightItem("SSCC processed dir (se crea)", processed_dir, False),
        PreflightItem("SSCC rt out (se genera)", rt_out, False),
        PreflightItem("SSCC infra out (se genera)", infra_out, False),
        PreflightItem("SSCC empresas out (se genera)", emp_out, False),
    ]

    r = make_result("sscc", items, mode=mode)

    # Si estás en strict y hay ambigüedad, puedes hacer que falle:
    if mode != "skip" and raw_dir.exists():
        tipo3 = (tipo[:3] or "").lower()
        # mismo patrón que arriba, pero devolviendo todos
        import re
        pat = re.compile(
            rf"^1[_\-\s]*CUADROS[_\-\s]*PAGO[_\-\s]*SSCC[_\-\s]*{re.escape(periodo)}.*{re.escape(tipo3)}.*\.xlsm$",
            re.IGNORECASE,
        )
        matches = [p for p in raw_dir.glob("*.xlsm") if pat.match(p.name)]
        if len(matches) > 1:
            # agregamos un missing “por ambigüedad” (lo tratamos como requerido)
            r.missing = [it for it in r.missing if "SSCC input xlsm" not in it.label]
            r.missing.append(
                PreflightItem(
                    f"SSCC input xlsm ambiguo: {len(matches)} archivos matchean (ejemplo)",
                    matches[0],
                    True,
                )
            )

    return r


def procesar_sscc(fecha: str, tipo: str = "Definitivo") -> None:
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    cuadro_pago = f"1_CUADROS_PAGO_SSCC_{periodo}_{tipo[:3].lower()}.xlsm"

    ruta_base = Path(__file__).resolve().parent.parent
    ruta_raw = ruta_base / "data" / "raw"
    ruta_processed = ruta_base / "data" / "processed"

    ruta_descarga = ruta_raw / "sscc" / str(año) / periodo
    ruta_carga = ruta_processed / "sscc" / str(año) / periodo

    os.makedirs(ruta_carga, exist_ok=True)

    print(f"Procesando {cuadro_pago}...")
    ini = time.time()

    archivo_xlsm = ruta_descarga / cuadro_pago
    if not archivo_xlsm.exists():
        raise FileNotFoundError(f"No existe el archivo SSCC: {archivo_xlsm}")

    # ----- Recurso Técnico -----
    df = pd.read_excel(
        archivo_xlsm,
        sheet_name="01.SSCC_Recurso_Técnico",
        header=None,
    )

    inicio = df[df[1] == "Concepto"].index[0]
    fin = df[df[1] == "CO ERNC"].index[-1]

    tabla_rt = df.loc[inicio + 1 : fin, list(range(1, 6))]
    tabla_rt.columns = ["concepto", "empresa", "recibe", "paga", "sen"]
    tabla_rt = tabla_rt.dropna(subset=["empresa"])
    tabla_rt = tabla_rt[
        ~(
            (tabla_rt["recibe"] == 0)
            & (tabla_rt["paga"] == 0)
            & (tabla_rt["sen"] == 0)
        )
    ]

    rt = f"sscc_rt_{periodo}.csv"
    tabla_rt.to_csv(
        ruta_carga / rt,
        index=False,
        sep=",",
        decimal=".",
        encoding="utf-8",
    )
    print(f"{rt} guardado en {ruta_carga}.")

    # ----- Infraestructura -----
    df = pd.read_excel(
        archivo_xlsm,
        sheet_name="02.SSCC_Infraestruct",
        header=None,
    )

    inicio2 = df[df[2] == "Empresa"].index[0]
    fin2 = df[df[1] == "INFRAESTRUCTURA"].index[-1]

    tabla_infra = df.loc[inicio2 + 1 : fin2, list(range(2, 6))]
    tabla_infra.columns = ["empresa", "remuneracion", "recaudacion", "neto"]
    tabla_infra = tabla_infra.dropna(subset=["empresa"])
    tabla_infra = tabla_infra[
        ~(
            (tabla_infra["remuneracion"] == 0)
            & (tabla_infra["recaudacion"] == 0)
            & (tabla_infra["neto"] == 0)
        )
    ]

    infra = f"sscc_infra_{periodo}.csv"
    tabla_infra.to_csv(
        ruta_carga / infra,
        index=False,
        sep=",",
        decimal=".",
        encoding="utf-8",
    )
    print(f"{infra} guardado en {ruta_carga}.")

    # ----- Empresas (si lo usas después, lo dejamos generado igual) -----
    empresas = pd.read_excel(
        archivo_xlsm,
        sheet_name="EMPRESAS",
        usecols="B:C",
    )
    empresas = empresas.dropna()
    empresas = empresas[~(empresas["RUT"] == "desactivado")]
    empresas = empresas[~(empresas["RUT"] == "reemplazada")]

    emp = f"empresas_sscc_{periodo}.csv"
    empresas.to_csv(
        ruta_carga / emp,
        index=False,
        sep=",",
        encoding="utf-8",
    )

    end = time.time()
    print("Proceso terminado.")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(end - ini))}.")


def importar_sscc(cx: Connection, cursor: Cursor, fecha: str) -> None:
    """
    PART1 (staging): carga a importar.sscc_rt e importar.sscc_infra.
    Aquí SÍ hacemos commit.
    """
    date = pd.to_datetime(fecha)
    año = date.year
    numero_mes = date.month
    nombre_mes = date.month_name(locale="es_CL.utf8")
    periodo = f"{str(año)[-2:]}{numero_mes:02d}"

    ruta_base = Path(__file__).resolve().parent.parent
    ruta_carga = ruta_base / "data" / "processed" / "sscc" / str(año) / periodo

    rt_csv = (ruta_carga / f"sscc_rt_{periodo}.csv").resolve()
    rt_csv_str = str(rt_csv).replace("\\", "/")
    infra_csv = (ruta_carga / f"sscc_infra_{periodo}.csv").resolve()
    infra_csv_str = str(infra_csv).replace("\\", "/")

    for p in (rt_csv, infra_csv):
        if not p.exists():
            raise FileNotFoundError(f"Falta archivo requerido para staging SSCC: {p}")

    print(f"Importando sscc {año} {nombre_mes} (staging)...")
    ini = time.time()

    #Crear tabla importar.sscc_rt si no existe 
    create_table_query = """
    CREATE TABLE IF NOT EXISTS importar.sscc_rt (
    concepto   VARCHAR(255) NOT NULL,
    empresa    VARCHAR(255) NOT NULL,
    recibe     FLOAT,
    paga       FLOAT,
    sen        FLOAT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    cursor.execute(create_table_query)

    cursor.execute("TRUNCATE TABLE importar.sscc_rt;")
    q1 = f"""
        LOAD DATA LOCAL INFILE '{rt_csv_str}'
        INTO TABLE importar.sscc_rt
        CHARACTER SET UTF8MB4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
        LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES;
    """
    cursor.execute(q1)

    #Crear tabla importar.sscc_infra si no existe
    create_table_query="""
    CREATE TABLE IF NOT EXISTS importar.sscc_infra (
    empresa       VARCHAR(255) NOT NULL,
    remuneracion  FLOAT,
    recaudacion   FLOAT,
    neto          FLOAT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    cursor.execute(create_table_query)

    cursor.execute("TRUNCATE TABLE importar.sscc_infra;")
    q2 = f"""
        LOAD DATA LOCAL INFILE '{infra_csv_str}'
        INTO TABLE importar.sscc_infra
        CHARACTER SET UTF8MB4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
        LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES;
    """
    cursor.execute(q2)

    cx.commit()

    final = time.time()
    print("sscc importado con éxito (staging).")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")


def revisar_sscc(cursor: Cursor) -> None:
    print("Revisando sscc...")

    e = """
        SELECT t.empresa
        FROM (SELECT DISTINCT empresa FROM importar.sscc_rt) t
        LEFT JOIN importar.empresa2 e2 ON e2.col_7 = t.empresa
        LEFT JOIN balance.empresa e ON e.nombre = e2.nombreempresa
        WHERE e.id IS NULL;
    """
    cursor.execute(e)
    reve = cursor.fetchall()
    if reve:
        print("REVISAR EMPRESAS SSCC_RT!")
        input("Presione ENTER para continuar...")

    e2 = """
        SELECT t.empresa
        FROM (SELECT DISTINCT empresa FROM importar.sscc_infra) t
        LEFT JOIN importar.empresa2 e2 ON e2.col_7 = t.empresa
        LEFT JOIN balance.empresa e ON e.nombre = e2.nombreempresa
        WHERE e.id IS NULL;
    """
    cursor.execute(e2)
    reve2 = cursor.fetchall()
    if reve2:
        print("REVISAR EMPRESAS SSCC_INFRA!")
        input("Presione ENTER para continuar...")


def cargar_sscc(
    cx: Connection,
    cursor: Cursor,
    fecha: str,
    tipo: str = "Definitivo",
    do_commit: bool = False,
) -> None:
    """
    PART2 (final): inserta en balance.sscc_rt y balance.sscc_infra.
    NO hace commit: el main decide commit/rollback.
    """
    date = pd.to_datetime(fecha)
    año = date.year
    nombre_mes = date.month_name(locale="es_CL.utf8")

    print(f"Cargando sscc {año} {nombre_mes} (final)...")
    ini = time.time()

    carga_rt = f"""
        INSERT INTO balance.sscc_rt
        SELECT
            v.id,
            t.concepto,
            e.id,
            t.recibe,
            t.paga,
            t.sen
        FROM importar.sscc_rt t
        LEFT JOIN balance.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        LEFT JOIN importar.empresa2 e2
            ON e2.col_7 = t.empresa
        LEFT JOIN balance.empresa e
            ON e.nombre = e2.nombreempresa;
    """
    cursor.execute(carga_rt)

    carga_infra = f"""
        INSERT INTO balance.sscc_infra
        SELECT
            v.id,
            e.id,
            t.remuneracion,
            t.recaudacion,
            t.neto
        FROM importar.sscc_infra t
        LEFT JOIN balance.version v
            ON v.periodo = '{fecha}'
           AND v.tipo    = '{tipo.upper()}'
        LEFT JOIN importar.empresa2 e2
            ON e2.col_7 = t.empresa
        LEFT JOIN balance.empresa e
            ON e.nombre = e2.nombreempresa;
    """
    cursor.execute(carga_infra)

    if not do_commit:
        print("⚠️  cargar_sscc ejecutado en modo DRY (sin commit; lo decide el main).")

    final = time.time()
    print("sscc: INSERTs ejecutados.")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - ini))}.")