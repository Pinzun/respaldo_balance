# init_stage.py
import re 
import os
import pymysql
import time
import threading
from pathlib import Path
import paramiko
from .db_utils import (
    SSH_HOST, SSH_PORT,SSH_USER,SSH_PASSWORD,
    DB_HOST_REMOTE,DB_PORT_REMOTE, DB_USER, DB_PASSWORD,
    _get_free_local_port, _forward_tunnel, _log,
    close_connection
)

def open_connection_no_db():
    """Túnel SSH sin seleccionar DB, necesario para CREATE DATABASE."""
    client=paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        SSH_HOST, port=SSH_PORT,
        username=SSH_USER, password=SSH_PASSWORD,
        look_for_keys=False, allow_agent=False,
    )

    transport =  client.get_transport()
    local_port = _get_free_local_port()
    stop_event=threading.Event()
    threads_bucket=[]
    client._dbutils_threads = threads_bucket

    threading.Thread(
        target=_forward_tunnel,
        args=(local_port,DB_HOST_REMOTE,DB_PORT_REMOTE,
              transport, stop_event, threads_bucket),
              daemon=True,
    ).start()

    time.sleep(0.5)

    conn=pymysql.connect(
        host="127.0.0.1",
        port=local_port,
        user=DB_USER,
        password=DB_PASSWORD,
        # SIN DATABASE
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=20,
        read_timeout=60,
        charset="utf8mb4",
        use_unicode=True,
    )

    _log(f"🔐 Conexión sin BD abierta (SSH: {SSH_HOST})")
    return conn, client, stop_event

def ejecutar_script_sql(conn, sql_path: str):
    """Ejecuta el archivo sql crear_importar.sql, limpiando comentarios y dividiendo ejecuciones por ';'"""
    sql =Path(sql_path).read_text(encoding="utf-8")
    # Elimina comentarios -- y bloques /* */
    sql = re.sub(r"--[^\n]*", "", sql)
    sql = re.sub(r"/\.?\*/", "", sql, flags=re.DOTALL)

    statements  = [s.strip() for s in sql.split(";") if s.strip()]

    print(f"\n📄 {len(statements)} sentencias encontradas en '{sql_path}'")
    print("-" * 60)

    with conn.cursor() as cursor:
        for i, stmt in enumerate(statements, 1):
            preview = " ".join(stmt.split())[:65] #colapsa saltos de líneas
            print(f" [{i:02d}/{len(statements)}] {preview}...")
            cursor.execute(stmt)

        conn.commit()
        print("-" * 60)
        print(f"✅ Script ejecutado: {len(statements)} sentencias OK\n")

def inicializar_stage():
    sql_path = Path(__file__).resolve().parent / "crea_importar.sql"
    print(f"📂 Buscando SQL en: {sql_path}")  # temporal para verificar
    
    if not sql_path.exists():
        raise FileNotFoundError(f"No se encuentra el archivo: {sql_path}")
    
    conn, ssh_client, stop_event = open_connection_no_db()
    try:
        ejecutar_script_sql(conn, str(sql_path))  # ← convierte a string explícitamente
        print("🎉 BD importar_balance y tablas creadas correctamente.")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        close_connection(conn, ssh_client, stop_event)

if __name__ == "__main__":
    inicializar_stage()

