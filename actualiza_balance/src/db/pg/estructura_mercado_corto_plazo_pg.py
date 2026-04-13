# estructura_mercado_corto_plazo_pg.py
"""
Crea la base de datos mercado_corto_plazo y su estructura completa
en PostgreSQL, ejecutando estructura_mercado_corto_plazo.sql.

A diferencia de crea_importar_pg.py (que solo crea un schema dentro
de una BD existente), este script necesita dos pasos:

  1. Conecta a la BD 'postgres' (admin) para crear la BD si no existe.
     CREATE DATABASE no puede ejecutarse dentro de una transacción.
  2. Conecta a 'mercado_corto_plazo' y ejecuta tablas, índices y vistas.

La sentencia CREATE DATABASE y el meta-comando \connect del archivo SQL
son manejados directamente por este script y se filtran antes de la
ejecución masiva de sentencias.
"""
import re
import psycopg2
import psycopg2.extras
from pathlib import Path

from ..db_utils_pg import (
    open_connection,
    open_connection_direct,
    _log,
    PG_HOST,
    PG_PORT,
    PG_USER,
    PG_PASSWORD,
    PG_DB,
)

SQL_FILE  = Path(__file__).resolve().parent / "estructura_mercado_corto_plazo.sql"
ADMIN_DB  = "postgres"


def _leer_statements(sql_path: Path) -> list[str]:
    """
    Lee el archivo SQL, elimina comentarios y divide por ';'.
    Descarta sentencias CREATE DATABASE y meta-comandos psql (\connect, etc.)
    que se manejan fuera de este bucle.
    """
    sql = sql_path.read_text(encoding="utf-8")
    sql = re.sub(r"--[^\n]*",  "",  sql)
    sql = re.sub(r"/\*.*?\*/", "",  sql, flags=re.DOTALL)

    statements = [s.strip() for s in sql.split(";") if s.strip()]

    def _excluir(stmt: str) -> bool:
        low = stmt.lower()
        return (
            re.match(r"\\",                  stmt)     # meta-comandos psql
            or re.match(r"create\s+database", low)     # CREATE DATABASE
        )

    return [s for s in statements if not _excluir(s)]


def _conexion_admin(server_mode: str, tunnel=None):
    """
    Retorna una conexión a la BD 'postgres' (admin).
    En modo SSH reutiliza el tunnel ya abierto.
    """
    if server_mode == "ssh":
        if tunnel is None:
            raise RuntimeError("Se requiere tunnel SSH para conectar en modo ssh.")
        conn = psycopg2.connect(
            host     = "127.0.0.1",
            port     = tunnel.local_bind_port,
            user     = PG_USER,
            password = PG_PASSWORD,
            dbname   = ADMIN_DB,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
    else:
        conn, _, _ = open_connection_direct(dbname=ADMIN_DB)
    return conn


# estructura_mercado_corto_plazo_pg.py
"""
Crea la base de datos mercado_corto_plazo y su estructura completa
en PostgreSQL, ejecutando estructura_mercado_corto_plazo.sql.

A diferencia de crea_importar_pg.py (que solo crea un schema dentro
de una BD existente), este script necesita dos pasos:

  1. Conecta a la BD 'postgres' (admin) para crear la BD si no existe.
     CREATE DATABASE no puede ejecutarse dentro de una transacción.
  2. Conecta a 'mercado_corto_plazo' y ejecuta tablas, índices y vistas.

La sentencia CREATE DATABASE y el meta-comando \connect del archivo SQL
son manejados directamente por este script y se filtran antes de la
ejecución masiva de sentencias.
"""
import re
import psycopg2
import psycopg2.extras
from pathlib import Path

from ..db_utils_pg import (
    open_connection,
    open_connection_direct,
    _log,
    PG_HOST,
    PG_PORT,
    PG_USER,
    PG_PASSWORD,
    PG_DB,
)

SQL_FILE  = Path(__file__).resolve().parent / "estructura_mercado_corto_plazo.sql"
ADMIN_DB  = "postgres"


def _leer_statements(sql_path: Path) -> list[str]:
    """
    Lee el archivo SQL, elimina comentarios y divide por ';'.
    Descarta sentencias CREATE DATABASE y meta-comandos psql (\connect, etc.)
    que se manejan fuera de este bucle.
    """
    sql = sql_path.read_text(encoding="utf-8")
    sql = re.sub(r"--[^\n]*",  "",  sql)
    sql = re.sub(r"/\*.*?\*/", "",  sql, flags=re.DOTALL)

    statements = [s.strip() for s in sql.split(";") if s.strip()]

    def _excluir(stmt: str) -> bool:
        low = stmt.lower()
        return (
            re.match(r"\\",                  stmt)     # meta-comandos psql
            or re.match(r"create\s+database", low)     # CREATE DATABASE
        )

    return [s for s in statements if not _excluir(s)]


def _conexion_admin(server_mode: str, tunnel=None):
    """
    Retorna una conexión a la BD 'postgres' (admin).
    En modo SSH reutiliza el tunnel ya abierto.
    """
    if server_mode == "ssh":
        if tunnel is None:
            raise RuntimeError("Se requiere tunnel SSH para conectar en modo ssh.")
        conn = psycopg2.connect(
            host     = "127.0.0.1",
            port     = tunnel.local_bind_port,
            user     = PG_USER,
            password = PG_PASSWORD,
            dbname   = ADMIN_DB,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
    else:
        conn, _, _ = open_connection_direct(dbname=ADMIN_DB)
    return conn


def _conexion_destino(server_mode: str, tunnel=None):
    """
    Retorna una conexión a la BD destino (PG_DB = mercado_corto_plazo).
    En modo SSH reutiliza el tunnel ya abierto.
    """
    if server_mode == "ssh":
        if tunnel is None:
            raise RuntimeError("Se requiere tunnel SSH para conectar en modo ssh.")
        conn = psycopg2.connect(
            host     = "127.0.0.1",
            port     = tunnel.local_bind_port,
            user     = PG_USER,
            password = PG_PASSWORD,
            dbname   = PG_DB,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
    else:
        conn, _, _ = open_connection_direct(dbname=PG_DB)
    return conn


def _crear_base_de_datos(server_mode: str, tunnel=None):
    """
    Paso 1: crea la BD mercado_corto_plazo si no existe.
    Requiere autocommit=True (CREATE DATABASE no acepta transacciones).
    """
    conn = _conexion_admin(server_mode, tunnel)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (PG_DB,)
            )
            if cur.fetchone():
                _log(f"ℹ️  La base de datos '{PG_DB}' ya existe, se omite CREATE DATABASE.")
            else:
                cur.execute(f'CREATE DATABASE "{PG_DB}" ENCODING \'UTF8\'')
                _log(f"✅ Base de datos '{PG_DB}' creada.")
    finally:
        conn.close()


def _ejecutar_estructura(server_mode: str, tunnel=None):
    statements = _leer_statements(SQL_FILE)
    total = len(statements)

    print(f"\n📄 {total} sentencias encontradas en '{SQL_FILE.name}'")
    print("-" * 60)

    conn = _conexion_destino(server_mode, tunnel)
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            # Crear schema primero si no existe
            cursor.execute("CREATE SCHEMA IF NOT EXISTS mercado_corto_plazo")
            cursor.execute("SET search_path TO mercado_corto_plazo")
            
            for i, stmt in enumerate(statements, 1):
                # Saltar SET search_path y CREATE SCHEMA del SQL (ya los ejecutamos)
                low = stmt.lower()
                if low.startswith("set search_path") or low.startswith("create schema"):
                    continue
                preview = " ".join(stmt.split())[:65]
                print(f" [{i:02d}/{total}] {preview}...")
                cursor.execute(stmt)
        print("-" * 60)
        print(f"✅ Estructura ejecutada: {total} sentencias OK\n")
    finally:
        conn.autocommit = False
        conn.close()


def crear_estructura_mercado_corto_plazo(server_mode: str = "direct"):
    """
    Punto de entrada principal.

    Args:
        server_mode: "direct" (conexión local) o "ssh" (a través de túnel SSH).
    """
    if not SQL_FILE.exists():
        raise FileNotFoundError(f"No se encuentra el archivo SQL: {SQL_FILE}")

    _log(f"📂 Script SQL : {SQL_FILE}")
    _log(f"🔧 Modo       : {server_mode}")

    tunnel = None
    try:
        if server_mode == "ssh":
            # Abrimos el túnel una sola vez y lo reutilizamos en ambos pasos.
            _, tunnel, _ = open_connection()

        _crear_base_de_datos(server_mode, tunnel)
        _ejecutar_estructura(server_mode, tunnel)
        _log(f"🎉 Base de datos '{PG_DB}' inicializada correctamente.")

    except Exception as e:
        print(f"❌ Error al inicializar la estructura: {e}")
        raise
    finally:
        if tunnel:
            try:
                tunnel.stop()
            except Exception:
                pass


if __name__ == "__main__":
    crear_estructura_mercado_corto_plazo()


def _crear_base_de_datos(server_mode: str, tunnel=None):
    """
    Paso 1: crea la BD mercado_corto_plazo si no existe.
    Requiere autocommit=True (CREATE DATABASE no acepta transacciones).
    """
    conn = _conexion_admin(server_mode, tunnel)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (PG_DB,)
            )
            if cur.fetchone():
                _log(f"ℹ️  La base de datos '{PG_DB}' ya existe, se omite CREATE DATABASE.")
            else:
                cur.execute(f'CREATE DATABASE "{PG_DB}" ENCODING \'UTF8\'')
                _log(f"✅ Base de datos '{PG_DB}' creada.")
    finally:
        conn.close()


def _ejecutar_estructura(server_mode: str, tunnel=None):
    """
    Paso 2: ejecuta todas las sentencias de estructura (tablas, índices, vistas)
    en la BD mercado_corto_plazo.
    """
    statements = _leer_statements(SQL_FILE)
    total = len(statements)

    print(f"\n📄 {total} sentencias encontradas en '{SQL_FILE.name}'")
    print("-" * 60)

    conn = _conexion_destino(server_mode, tunnel)
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            for i, stmt in enumerate(statements, 1):
                preview = " ".join(stmt.split())[:65]
                print(f" [{i:02d}/{total}] {preview}...")
                cursor.execute(stmt)
        print("-" * 60)
        print(f"✅ Estructura ejecutada: {total} sentencias OK\n")
    finally:
        conn.autocommit = False
        conn.close()


def crear_estructura_mercado_corto_plazo(server_mode: str = "direct"):
    """
    Punto de entrada principal.

    Args:
        server_mode: "direct" (conexión local) o "ssh" (a través de túnel SSH).
    """
    if not SQL_FILE.exists():
        raise FileNotFoundError(f"No se encuentra el archivo SQL: {SQL_FILE}")

    _log(f"📂 Script SQL : {SQL_FILE}")
    _log(f"🔧 Modo       : {server_mode}")

    tunnel = None
    try:
        if server_mode == "ssh":
            # Abrimos el túnel una sola vez y lo reutilizamos en ambos pasos.
            _, tunnel, _ = open_connection()

        _crear_base_de_datos(server_mode, tunnel)
        _ejecutar_estructura(server_mode, tunnel)
        _log(f"🎉 Base de datos '{PG_DB}' inicializada correctamente.")

    except Exception as e:
        print(f"❌ Error al inicializar la estructura: {e}")
        raise
    finally:
        if tunnel:
            try:
                tunnel.stop()
            except Exception:
                pass


if __name__ == "__main__":
    crear_estructura_mercado_corto_plazo()
