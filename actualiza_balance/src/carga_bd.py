# main.py

import time
from pathlib import Path
from datetime import date
# -----------------------------
# Procesamiento + importación
# -----------------------------
from actualiza_balance.src.core.cmg import procesar_cmg, importar_cmg, revisar_cmg, cargar_cmg, preflight_cmg
from actualiza_balance.src.core.barras import (
    procesar_barras,
    importar_barras,
    revisar_barras_info,
    cargar_barras_info,
    preflight_barras,
)
from actualiza_balance.src.core.balance import (
    procesar_medidas,
    importar_balance,
    revisar_balance,
    cargar_balance,
    preflight_balance,
)
from actualiza_balance.src.core.factor_retiro_regulado import (
    procesar_frr,
    importar_frr,
    revisar_frr,
    cargar_frr,
    preflight_frr,
)
from actualiza_balance.src.core.precio_estabilizado import (
    procesar_compensacion,
    procesar_inyecciones,
    importar_pe,
    revisar_compensacion,
    revisar_inyecciones,
    cargar_compensacion,
    cargar_inyecciones,
    preflight_precio_estabilizado,
)
from actualiza_balance.src.core.contratos import (
    importar_contratos,
    revisar_contratos,
    cargar_contratos,
    preflight_contratos,
)
from actualiza_balance.src.core.sobrecostos import (
    procesar_sobrecostos,
    importar_sobrecostos,
    revisar_sobrecostos,
    cargar_sobrecostos,
    preflight_sobrecostos,
)
from scripts.cv_op import (
    procesar_po,
    importar_cv_op,
    revisar_cv_op,
    cargar_op,
    preflight_cv_op,
)
from actualiza_balance.src.core.sscc import (
    procesar_sscc,
    importar_sscc,
    revisar_sscc,
    cargar_sscc,
    preflight_sscc,
)

# Si cmg_real ya lo tienes operativo, ideal agregarle preflight también.
from scripts.cmg_real import (
    procesar_cmg_real,
    importar_cmg_real,
    revisar_cmg_real,
    cargar_cmg_real,
    preflight_cmg_real,
)

from scripts.crea_base_staging import crea_staging

# -----------------------------
# DB utils
# -----------------------------
from src.db_utils import open_connection, close_connection, open_connection_direct, close_connection_direct

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
        preflight_cv_op(fecha, mode=mode),
        preflight_sscc(fecha, tipo, mode=mode),
        # cuando lo integres:
        # preflight_reducciones(fecha, tipo, mode=mode),
        preflight_cmg_real(fecha, tipo, mode=mode),
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

    if can_run.get("cv_op"):
        procesar_po(fecha)

    if can_run.get("sscc"):
        procesar_sscc(fecha, tipo)

    # cmg_real (si no tiene preflight, lo dejamos protegido por can_run)
    if can_run.get("cmg_real"):
        procesar_cmg_real(fecha)

    # --- Importación a DB (staging) ---

    # Garantiza la existencia de la base para staging
    crea_staging(conexion, cursor)

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

    if can_run.get("cv_op"):
        importar_cv_op(conexion, cursor, fecha)

    if can_run.get("sscc"):
        importar_sscc(conexion, cursor, fecha)

    if can_run.get("cmg_real"):
        importar_cmg_real(conexion, cursor, fecha)

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

    if can_run.get("cv_op"):
        revisar_cv_op(cursor)
        cargar_op(conexion, cursor, do_commit)

    if can_run.get("sscc"):
        revisar_sscc(cursor)
        cargar_sscc(conexion, cursor, fecha, tipo, do_commit)

    if can_run.get("cmg_real"):
        revisar_cmg_real(cursor)
        cargar_cmg_real(conexion, cursor, do_commit)

    final = time.time()
    print(f"[PART2] Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")

def carga_bd(fecha_inicio: date,
             tipo: str, 
             mode: str = "skip", 
             server_mode: str = "direct", 
             dry_run: bool = True,
             part1_exec: bool = False,
             part2_exec: bool = False
             ):
    do_commit = not dry_run
    # Parámetros de ejecución 
    #fecha = "2025-10-01"
    fecha = fecha_inicio.strftime("%Y-%m-%d")
    # Normaliza tipo (evita bugs con joins a balance.version.tipo)
    tipo = tipo.strip().capitalize()  # "Definitivo" / "Preliminar"
    
    # --------------------
    # PREFLIGHTS
    # --------------------
    _, can_run = run_preflights(fecha, tipo, mode=mode)

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
        if server_mode == "direct":
            conn, ssh_client, stop_event = open_connection_direct()
        if server_mode == "ssh":    
            conn, ssh_client, stop_event = open_connection()
        try:
            with conn.cursor() as cursor:
                part1(conn, cursor, fecha, tipo, can_run)

            # PART1 suele hacer commits internos (staging), pero dejamos este commit por seguridad
            conn.commit()
            print("✅ Commit realizado para PART1.")
        finally:
            if server_mode == "direct":
                close_connection_direct(conn, ssh_client, stop_event)
            if server_mode == "ssh":    
                close_connection(conn, ssh_client, stop_event)


    if part2_exec == True:
        # --------------------
        # PART2
        # --------------------
        
        if server_mode == "direct":
            conn, ssh_client, stop_event = open_connection_direct()
        if server_mode == "ssh":
            conn, ssh_client, stop_event = open_connection()
        try:
            conn.autocommit(False)  
            with conn.cursor() as cursor:
                part2(conn, cursor, fecha, tipo, can_run, do_commit)

                if dry_run:
                    conn.rollback()
                    print("⚠️  Dry run: ROLLBACK ejecutado (PART2 no dejó cambios)")
                else:
                    conn.commit()
                    print("✅ Commit realizado para PART2.")
        finally:
            if server_mode == "direct":
                close_connection_direct(conn, ssh_client, stop_event)
            if server_mode == "ssh":    
                close_connection(conn, ssh_client, stop_event)

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



