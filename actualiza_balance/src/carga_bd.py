# main.py

import time
from pathlib import Path
from datetime import date
# -----------------------------
# Procesamiento + importación (MySQL — importaciones por defecto)
# -----------------------------
from actualiza_balance.src.core.mariaDB.cmg import procesar_cmg, importar_cmg, revisar_cmg, cargar_cmg, preflight_cmg
from actualiza_balance.src.core.mariaDB.barras import (
    procesar_barras,
    importar_barras,
    revisar_barras_info,
    cargar_barras_info,
    preflight_barras,
)
from actualiza_balance.src.core.mariaDB.balance import (
    procesar_medidas,
    importar_balance,
    revisar_balance,
    cargar_balance,
    preflight_balance,
)
from actualiza_balance.src.core.mariaDB.factor_retiro_regulado import (
    procesar_frr,
    importar_frr,
    revisar_frr,
    cargar_frr,
    preflight_frr,
)
from actualiza_balance.src.core.mariaDB.precio_estabilizado import (
    procesar_compensacion,
    procesar_inyecciones,
    importar_pe,
    revisar_compensacion,
    revisar_inyecciones,
    cargar_compensacion,
    cargar_inyecciones,
    preflight_precio_estabilizado,
)
from actualiza_balance.src.core.mariaDB.contratos import (
    importar_contratos,
    revisar_contratos,
    cargar_contratos,
    preflight_contratos,
)
from actualiza_balance.src.core.mariaDB.sobrecostos import (
    procesar_sobrecostos,
    importar_sobrecostos,
    revisar_sobrecostos,
    cargar_sobrecostos,
    preflight_sobrecostos,
)

from actualiza_balance.src.core.mariaDB.sscc import (
    procesar_sscc,
    importar_sscc,
    revisar_sscc,
    cargar_sscc,
    preflight_sscc,
)



# -----------------------------
# DB utils (MySQL — por defecto) + router unificado
# -----------------------------
from actualiza_balance.src.db.db_utils import open_connection, close_connection, open_connection_direct, close_connection_direct
from actualiza_balance.src.db.router import get_connection, release_connection

def run_preflights(fecha: str, tipo: str, mode: str = "skip"):
    """
    mode:
      - "skip": si faltan inputs requeridos => SKIP (no es error)
      - "strict": si faltan inputs requeridos => FAIL (error)
    """
    results = [
        preflight_cmg(fecha, tipo, mode=mode),
        preflight_barras(fecha, mode=mode),
        preflight_balance(fecha, tipo, mode=mode),
        preflight_frr(fecha, mode=mode),
        preflight_precio_estabilizado(fecha, tipo, mode=mode),
        preflight_contratos(fecha, tipo, mode=mode),
        preflight_sobrecostos(fecha, mode=mode),
        preflight_sscc(fecha, tipo, mode=mode),
        # cuando lo integres:
        # preflight_reducciones(fecha, tipo, mode=mode),
    ]

    for r in results:
        r.print_report()

    ok = sum(r.ok for r in results)
    skip = sum(getattr(r, "skip", False) for r in results)
    fail = sum(getattr(r, "fail", False) for r in results)

    print(f"\n📌 PREFLIGHT RESUMEN :: OK={ok} | SKIP={skip} | FAIL={fail} | mode={mode}")

    # SOLO falla si hay FAIL reales (errores estructurales / strict)
    if fail:
        raise RuntimeError("❌ Preflight FAIL: hay módulos con errores en modo estricto o inconsistencias.")

    can_run = {r.module: r.ok for r in results}
    return results, can_run

def part1(conexion, cursor, fecha, tipo, can_run):
    """
    PARTE 1: procesamiento + importación a tablas staging/importar.
    Se ejecuta SOLO lo que esté OK en can_run.
    """
    inicio = time.time()

    # --- Procesamiento ---
    if can_run.get("cmg"):
        procesar_cmg(fecha, tipo)

    if can_run.get("barras"):
        procesar_barras(fecha)

    if can_run.get("balance"):
        procesar_medidas(fecha, tipo)

    if can_run.get("factor_retiro_regulado"):
        procesar_frr(fecha)

    if can_run.get("precio_estabilizado"):
        procesar_compensacion(fecha, tipo)
        procesar_inyecciones(fecha, tipo)

    if can_run.get("sobrecostos"):
        procesar_sobrecostos(fecha)


    if can_run.get("sscc"):
        procesar_sscc(fecha, tipo)


    if can_run.get("cmg"):
        importar_cmg(conexion, cursor, fecha)

    if can_run.get("barras"):
        importar_barras(conexion, cursor, fecha)

    if can_run.get("balance"):
        importar_balance(conexion, cursor, fecha, tipo)

    if can_run.get("factor_retiro_regulado"):
        importar_frr(conexion, cursor, fecha)

    if can_run.get("precio_estabilizado"):
        importar_pe(conexion, cursor, fecha)

    if can_run.get("contratos"):
        importar_contratos(conexion, cursor, fecha, tipo)

    if can_run.get("sobrecostos"):
        importar_sobrecostos(conexion, cursor, fecha)

    if can_run.get("sscc"):
        importar_sscc(conexion, cursor, fecha)


    final = time.time()
    print(f"[PART1] Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")

def part2(conexion, cursor, fecha, tipo, can_run, do_commit):
    """
    PARTE 2: revisión + carga definitiva en balance.*
    Se ejecuta SOLO lo que esté OK en can_run.
    (El commit/rollback lo controla el main.)
    """
    inicio = time.time()

    if can_run.get("cmg"):
        revisar_cmg(cursor)
        cargar_cmg(conexion, cursor, fecha, tipo, do_commit)

    if can_run.get("barras"):
        revisar_barras_info(cursor)
        cargar_barras_info(conexion, cursor, fecha, tipo, do_commit)

    if can_run.get("balance"):
        revisar_balance(cursor)
        cargar_balance(conexion, cursor, fecha, tipo, do_commit)

    if can_run.get("factor_retiro_regulado"):
        revisar_frr(cursor)
        cargar_frr(conexion, cursor, fecha, tipo, do_commit)

    if can_run.get("precio_estabilizado"):
        revisar_compensacion(cursor)
        cargar_compensacion(conexion, cursor, fecha, tipo, do_commit)

        revisar_inyecciones(cursor, fecha, tipo)
        cargar_inyecciones(conexion, cursor, fecha, tipo, do_commit)

    if can_run.get("contratos"):
        revisar_contratos(cursor)
        cargar_contratos(conexion, cursor, fecha, tipo, do_commit)

    if can_run.get("sobrecostos"):
        revisar_sobrecostos(cursor)
        cargar_sobrecostos(conexion, cursor, fecha, tipo, do_commit)

    if can_run.get("sscc"):
        revisar_sscc(cursor)
        cargar_sscc(conexion, cursor, fecha, tipo, do_commit)

    final = time.time()
    print(f"[PART2] Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")

def _load_core_pg():
    """Importa las funciones de core en su versión PostgreSQL."""
    from actualiza_balance.src.core.pg.cmg_pg import (
        procesar_cmg, importar_cmg, revisar_cmg, cargar_cmg, preflight_cmg,
    )
    from actualiza_balance.src.core.pg.barras_pg import (
        procesar_barras, importar_barras, revisar_barras_info,
        cargar_barras_info, preflight_barras,
    )
    from actualiza_balance.src.core.pg.balance_pg import (
        procesar_medidas, importar_balance, revisar_balance,
        cargar_balance, preflight_balance,
    )
    from actualiza_balance.src.core.pg.factor_retiro_regulado_pg import (
        procesar_frr, importar_frr, revisar_frr, cargar_frr, preflight_frr,
    )
    from actualiza_balance.src.core.pg.precio_estabilizado_pg import (
        procesar_compensacion, procesar_inyecciones, importar_pe,
        revisar_compensacion, revisar_inyecciones,
        cargar_compensacion, cargar_inyecciones, preflight_precio_estabilizado,
    )
    from actualiza_balance.src.core.pg.contratos_pg import (
        importar_contratos, revisar_contratos, cargar_contratos, preflight_contratos,
    )
    from actualiza_balance.src.core.pg.sobrecostos_pg import (
        procesar_sobrecostos, importar_sobrecostos, revisar_sobrecostos,
        cargar_sobrecostos, preflight_sobrecostos,
    )
    from actualiza_balance.src.core.pg.sscc_pg import (
        procesar_sscc, importar_sscc, revisar_sscc, cargar_sscc, preflight_sscc,
    )
    return {
        "procesar_cmg": procesar_cmg, "importar_cmg": importar_cmg,
        "revisar_cmg": revisar_cmg, "cargar_cmg": cargar_cmg,
        "preflight_cmg": preflight_cmg,
        "procesar_barras": procesar_barras, "importar_barras": importar_barras,
        "revisar_barras_info": revisar_barras_info, "cargar_barras_info": cargar_barras_info,
        "preflight_barras": preflight_barras,
        "procesar_medidas": procesar_medidas, "importar_balance": importar_balance,
        "revisar_balance": revisar_balance, "cargar_balance": cargar_balance,
        "preflight_balance": preflight_balance,
        "procesar_frr": procesar_frr, "importar_frr": importar_frr,
        "revisar_frr": revisar_frr, "cargar_frr": cargar_frr,
        "preflight_frr": preflight_frr,
        "procesar_compensacion": procesar_compensacion,
        "procesar_inyecciones": procesar_inyecciones,
        "importar_pe": importar_pe,
        "revisar_compensacion": revisar_compensacion,
        "revisar_inyecciones": revisar_inyecciones,
        "cargar_compensacion": cargar_compensacion,
        "cargar_inyecciones": cargar_inyecciones,
        "preflight_precio_estabilizado": preflight_precio_estabilizado,
        "importar_contratos": importar_contratos, "revisar_contratos": revisar_contratos,
        "cargar_contratos": cargar_contratos, "preflight_contratos": preflight_contratos,
        "procesar_sobrecostos": procesar_sobrecostos,
        "importar_sobrecostos": importar_sobrecostos,
        "revisar_sobrecostos": revisar_sobrecostos,
        "cargar_sobrecostos": cargar_sobrecostos,
        "preflight_sobrecostos": preflight_sobrecostos,
        "procesar_sscc": procesar_sscc, "importar_sscc": importar_sscc,
        "revisar_sscc": revisar_sscc, "cargar_sscc": cargar_sscc,
        "preflight_sscc": preflight_sscc,
    }


def carga_bd(fecha_inicio: date,
             tipo: str,
             mode: str = "skip",
             server_mode: str = "direct",
             dry_run: bool = True,
             part1_exec: bool = False,
             part2_exec: bool = False,
             db_engine: str = "mysql",
             ):
    do_commit = not dry_run
    fecha = fecha_inicio.strftime("%Y-%m-%d")
    # Normaliza tipo (evita bugs con joins a balance.version.tipo)
    tipo = tipo.strip().capitalize()  # "Definitivo" / "Preliminar"

    # Selecciona funciones de core según el motor
    if db_engine == "postgresql":
        _pg = _load_core_pg()
        _preflight_cmg = _pg["preflight_cmg"]
        _preflight_barras = _pg["preflight_barras"]
        _preflight_balance = _pg["preflight_balance"]
        _preflight_frr = _pg["preflight_frr"]
        _preflight_precio_estabilizado = _pg["preflight_precio_estabilizado"]
        _preflight_contratos = _pg["preflight_contratos"]
        _preflight_sobrecostos = _pg["preflight_sobrecostos"]
        _preflight_sscc = _pg["preflight_sscc"]
        _part1_fn = lambda conn, cur, f, t, cr: _part1_pg(conn, cur, f, t, cr, _pg)
        _part2_fn = lambda conn, cur, f, t, cr, dc: _part2_pg(conn, cur, f, t, cr, dc, _pg)
    else:
        _preflight_cmg = preflight_cmg
        _preflight_barras = preflight_barras
        _preflight_balance = preflight_balance
        _preflight_frr = preflight_frr
        _preflight_precio_estabilizado = preflight_precio_estabilizado
        _preflight_contratos = preflight_contratos
        _preflight_sobrecostos = preflight_sobrecostos
        _preflight_sscc = preflight_sscc
        _part1_fn = part1
        _part2_fn = part2

    # --------------------
    # PREFLIGHTS
    # --------------------
    results = [
        _preflight_cmg(fecha, tipo, mode=mode),
        _preflight_barras(fecha, mode=mode),
        _preflight_balance(fecha, tipo, mode=mode),
        _preflight_frr(fecha, mode=mode),
        _preflight_precio_estabilizado(fecha, tipo, mode=mode),
        _preflight_contratos(fecha, tipo, mode=mode),
        _preflight_sobrecostos(fecha, mode=mode),
        _preflight_sscc(fecha, tipo, mode=mode),
    ]

    for r in results:
        r.print_report()

    ok = sum(r.ok for r in results)
    skip = sum(getattr(r, "skip", False) for r in results)
    fail = sum(getattr(r, "fail", False) for r in results)
    print(f"\n📌 PREFLIGHT RESUMEN :: OK={ok} | SKIP={skip} | FAIL={fail} | mode={mode}")
    if fail:
        raise RuntimeError("❌ Preflight FAIL: hay módulos con errores.")

    can_run = {r.module: r.ok for r in results}

    # Dependencias mínimas (contratos depende de balance/procesar_medidas)
    if can_run.get("contratos") and not can_run.get("balance"):
        can_run["contratos"] = False

    if not any(can_run.values()):
        print("ℹ️ Todo está en SKIP (no hay insumos). Terminando sin abrir DB.")
        return

    if part1_exec == True:
        # --------------------
        # PART1
        # --------------------
        conn, ssh_client, stop_event = get_connection(server_mode, db_engine)
        try:
            with conn.cursor() as cursor:
                _part1_fn(conn, cursor, fecha, tipo, can_run)
            conn.commit()
            print("✅ Commit realizado para PART1.")
        finally:
            release_connection(conn, ssh_client, stop_event, db_engine, server_mode)

    if part2_exec == True:
        # --------------------
        # PART2
        # --------------------
        conn, ssh_client, stop_event = get_connection(server_mode, db_engine)
        try:
            # psycopg2: autocommit es una propiedad; pymysql: es un método
            if db_engine == "postgresql":
                conn.autocommit = False
            else:
                conn.autocommit(False)
            with conn.cursor() as cursor:
                _part2_fn(conn, cursor, fecha, tipo, can_run, do_commit)

                if dry_run:
                    conn.rollback()
                    print("⚠️  Dry run: ROLLBACK ejecutado (PART2 no dejó cambios)")
                else:
                    conn.commit()
                    print("✅ Commit realizado para PART2.")
        finally:
            release_connection(conn, ssh_client, stop_event, db_engine, server_mode)


def _part1_pg(conexion, cursor, fecha, tipo, can_run, pg):
    """Equivalente de part1() usando los módulos _pg."""
    inicio = time.time()

    if can_run.get("cmg"):
        pg["procesar_cmg"](fecha, tipo)
    if can_run.get("barras"):
        pg["procesar_barras"](fecha)
    if can_run.get("balance"):
        pg["procesar_medidas"](fecha, tipo)
    if can_run.get("factor_retiro_regulado"):
        pg["procesar_frr"](fecha)
    if can_run.get("precio_estabilizado"):
        pg["procesar_compensacion"](fecha, tipo)
        pg["procesar_inyecciones"](fecha, tipo)
    if can_run.get("sobrecostos"):
        pg["procesar_sobrecostos"](fecha)
    if can_run.get("sscc"):
        pg["procesar_sscc"](fecha, tipo)

    if can_run.get("cmg"):
        pg["importar_cmg"](conexion, cursor, fecha)
    if can_run.get("barras"):
        pg["importar_barras"](conexion, cursor, fecha)
    if can_run.get("balance"):
        pg["importar_balance"](conexion, cursor, fecha, tipo)
    if can_run.get("factor_retiro_regulado"):
        pg["importar_frr"](conexion, cursor, fecha)
    if can_run.get("precio_estabilizado"):
        pg["importar_pe"](conexion, cursor, fecha)
    if can_run.get("contratos"):
        pg["importar_contratos"](conexion, cursor, fecha, tipo)
    if can_run.get("sobrecostos"):
        pg["importar_sobrecostos"](conexion, cursor, fecha)
    if can_run.get("sscc"):
        pg["importar_sscc"](conexion, cursor, fecha)

    final = time.time()
    print(f"[PART1-PG] Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")


def _part2_pg(conexion, cursor, fecha, tipo, can_run, do_commit, pg):
    """Equivalente de part2() usando los módulos _pg."""
    inicio = time.time()

    if can_run.get("cmg"):
        pg["revisar_cmg"](cursor)
        pg["cargar_cmg"](conexion, cursor, fecha, tipo, do_commit)
    if can_run.get("barras"):
        pg["revisar_barras_info"](cursor)
        pg["cargar_barras_info"](conexion, cursor, fecha, tipo, do_commit)
    if can_run.get("balance"):
        pg["revisar_balance"](cursor)
        pg["cargar_balance"](conexion, cursor, fecha, tipo, do_commit)
    if can_run.get("factor_retiro_regulado"):
        pg["revisar_frr"](cursor)
        pg["cargar_frr"](conexion, cursor, fecha, tipo, do_commit)
    if can_run.get("precio_estabilizado"):
        pg["revisar_compensacion"](cursor)
        pg["cargar_compensacion"](conexion, cursor, fecha, tipo, do_commit)
        pg["revisar_inyecciones"](cursor, fecha, tipo)
        pg["cargar_inyecciones"](conexion, cursor, fecha, tipo, do_commit)
    if can_run.get("contratos"):
        pg["revisar_contratos"](cursor)
        pg["cargar_contratos"](conexion, cursor, fecha, tipo, do_commit)
    if can_run.get("sobrecostos"):
        pg["revisar_sobrecostos"](cursor)
        pg["cargar_sobrecostos"](conexion, cursor, fecha, tipo, do_commit)
    if can_run.get("sscc"):
        pg["revisar_sscc"](cursor)
        pg["cargar_sscc"](conexion, cursor, fecha, tipo, do_commit)

    final = time.time()
    print(f"[PART2-PG] Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")

'''    
if __name__ == "carga_bd":
    print("Módulo carga_bd ejecutandose en modo stage exclusivo")
    fecha = date(2025, 10, 01)
    tipo = "Definitivo"    
    carga_bd(fecha,
             tipo=tipo, 
             mode="skip", 
             server_mode="direct", 
             dry_run=True,
             part1_exec=True,
             part2_exec=False)
             '''



