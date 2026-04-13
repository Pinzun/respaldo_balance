# crea_importar_pg.py
"""
Equivalente PostgreSQL de crea_importar.py.

En MySQL se crean dos bases de datos separadas (balance e importar_balance).
En PostgreSQL se usa un único servidor con dos schemas dentro de la misma BD:
  - schema 'mercado_corto_plazo' → tablas definitivas
  - schema 'importar_mcp'        → tablas staging

Esta función conecta a la BD configurada (PG_DB) y ejecuta
crea_importar_pg.sql que crea el schema 'importar_mcp' y sus tablas.
"""
import re
from pathlib import Path

from ..db_utils_pg import (
    open_connection,
    open_connection_direct,
    close_connection,
    close_connection_direct,
    _log,
)


def open_connection_no_schema(server_mode: str = "direct"):
    """
    Abre conexión a PostgreSQL. Conecta a la BD configurada (PG_DB)
    para poder crear el schema 'importar' si no existe.
    """
    if server_mode == "ssh":
        return open_connection()
    else:
        return open_connection_direct()


def ejecutar_script_sql_pg(conn, sql_path: str):
    """
    Ejecuta un script SQL PostgreSQL, dividiendo por ';'
    y eliminando comentarios.
    """
    sql = Path(sql_path).read_text(encoding="utf-8")
    sql = re.sub(r"--[^\n]*", "", sql)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)

    statements = [s.strip() for s in sql.split(";") if s.strip()]
    print(f"\n📄 {len(statements)} sentencias encontradas en '{sql_path}'")
    print("-" * 60)

    conn.autocommit = True
    with conn.cursor() as cursor:
        for i, stmt in enumerate(statements, 1):
            preview = " ".join(stmt.split())[:65]
            print(f" [{i:02d}/{len(statements)}] {preview}...")
            cursor.execute(stmt)

    print("-" * 60)
    print(f"✅ Script ejecutado: {len(statements)} sentencias OK\n")


def inicializar_stage_pg(server_mode: str = "direct"):
    sql_path = Path(__file__).resolve().parent / "crea_importar_pg.sql"
    print(f"📂 Buscando SQL en: {sql_path}")

    if not sql_path.exists():
        raise FileNotFoundError(f"No se encuentra el archivo: {sql_path}")

    conn, tunnel, _ = open_connection_no_schema(server_mode=server_mode)
    try:
        ejecutar_script_sql_pg(conn, str(sql_path))
        print("🎉 Schema 'importar_mcp' y tablas creadas correctamente (PostgreSQL).")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        conn.autocommit = False
        try:
            conn.close()
        except Exception:
            pass
        try:
            if tunnel:
                tunnel.stop()
        except Exception:
            pass


if __name__ == "__main__":
    inicializar_stage_pg()
