"""
db_utils_pg.py — Equivalente PostgreSQL de db_utils.py.

Usa psycopg2 para la conexión y sshtunnel para el túnel SSH.
Expone la misma interfaz que db_utils.py:
  open_connection()        → (conn, tunnel, None)
  open_connection_direct() → (conn, None, None)
  close_connection()
  close_connection_direct()

Variables de entorno (prefijo PG_ para no colisionar con las de MySQL):
  PG_SSH_HOST, PG_SSH_PORT, PG_SSH_USER, PG_SSH_PASSWORD
  PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DB

El cursor devuelve dicts gracias a psycopg2.extras.RealDictCursor,
equivalente al DictCursor de pymysql.
"""

import os
from pathlib import Path

import psycopg2
import psycopg2.extras

try:
    from sshtunnel import SSHTunnelForwarder
    _HAS_SSHTUNNEL = True
except ImportError:
    _HAS_SSHTUNNEL = False

try:
    from dotenv import load_dotenv
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# ---------------------------
# CONFIGURACIÓN GLOBAL
# ---------------------------
PG_SSH_HOST = os.getenv("PG_SSH_HOST", "")
PG_SSH_PORT = int(os.getenv("PG_SSH_PORT", "22"))
PG_SSH_USER = os.getenv("PG_SSH_USER", "")
PG_SSH_PASSWORD = os.getenv("PG_SSH_PASSWORD", "")

PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_USER = os.getenv("PG_USER", "")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")
PG_DB = os.getenv("PG_DB", "mercado_corto_plazo")


def _log(msg: str):
    if os.getenv("DB_UTILS_QUIET") != "1":
        print(msg)


def open_connection():
    """
    Abre túnel SSH y retorna (conn, tunnel, None).
    Usa sshtunnel en vez de paramiko manual.
    El tercer elemento es None (mantiene la misma firma que db_utils.py).
    """
    if not _HAS_SSHTUNNEL:
        raise ImportError(
            "sshtunnel no está instalado. Ejecuta: pip install sshtunnel"
        )
    if not PG_SSH_HOST or not PG_SSH_USER:
        raise RuntimeError(
            "Faltan variables de entorno SSH (PG_SSH_HOST / PG_SSH_USER)."
        )
    if not PG_USER or not PG_DB:
        raise RuntimeError(
            "Faltan variables de entorno de BD (PG_USER / PG_DB)."
        )

    tunnel = SSHTunnelForwarder(
        (PG_SSH_HOST, PG_SSH_PORT),
        ssh_username=PG_SSH_USER,
        ssh_password=PG_SSH_PASSWORD,
        remote_bind_address=(PG_HOST, PG_PORT),
    )
    tunnel.start()

    conn = psycopg2.connect(
        host="127.0.0.1",
        port=tunnel.local_bind_port,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname=PG_DB,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )

    _log(f"🔐 Conexión abierta: PostgreSQL ({PG_DB}) a través de SSH ({PG_SSH_HOST})")
    return conn, tunnel, None


def close_connection(conn, tunnel, stop_event=None):
    """Cierra la conexión PostgreSQL y el túnel SSH."""
    try:
        if conn:
            conn.close()
            _log("✅ Conexión PostgreSQL cerrada.")
    except Exception as e:
        _log(f"⚠️ Error al cerrar PostgreSQL: {e}")

    try:
        if tunnel:
            tunnel.stop()
            _log("🔌 Túnel SSH cerrado.")
    except Exception as e:
        _log(f"⚠️ Error al cerrar túnel SSH: {e}")


def open_connection_direct(
    host: str | None = None,
    port: int | None = None,
    dbname: str | None = None,
    options: str | None = None,     # ← agregar

):
    """
    Conecta directamente a PostgreSQL sin túnel SSH.
    Retorna (conn, None, None) para mantener la misma firma que db_utils.py.
    """
    host = host or PG_HOST
    port = port or PG_PORT
    dbname = dbname or PG_DB

    if not host:
        raise RuntimeError("Falta host de PostgreSQL (PG_HOST).")
    if not PG_USER or not dbname:
        raise RuntimeError("Faltan variables de entorno PG_USER / PG_DB.")

    conn = psycopg2.connect(
        host=host,
        port=port,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname=dbname,
        options=options,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )

    _log(f"🗄️ Conexión directa abierta: PostgreSQL ({dbname}) en {host}:{port}")
    return conn, None, None


def close_connection_direct(conn, tunnel=None, stop_event=None):
    """Cierra una conexión directa a PostgreSQL."""
    try:
        if conn:
            conn.close()
            _log("✅ Conexión PostgreSQL cerrada (directa).")
    except Exception as e:
        _log(f"⚠️ Error al cerrar PostgreSQL (directa): {e}")
