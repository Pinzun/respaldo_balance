"""
router.py — Módulo de routing de conexiones de BD.

Expone una interfaz unificada para obtener y liberar conexiones
independientemente del motor de BD (mysql | postgresql).
"""
from typing import Tuple, Any


def get_connection(server_mode: str, db_engine: str) -> Tuple[Any, Any, Any]:
    """
    Retorna (conn, ssh_client_or_tunnel, stop_event) según el motor y modo.

    Para MySQL:    stop_event es un threading.Event (puede ser None en direct)
    Para PostgreSQL: stop_event siempre es None (sshtunnel gestiona sus propios hilos)
    """
    if db_engine == "postgresql":
        from .db_utils_pg import (
            open_connection as pg_ssh,
            open_connection_direct as pg_direct,
        )
        if server_mode == "ssh":
            return pg_ssh()
        else:
            return pg_direct()
    else:
        from .db_utils import (
            open_connection as my_ssh,
            open_connection_direct as my_direct,
        )
        if server_mode == "ssh":
            return my_ssh()
        else:
            return my_direct()


def release_connection(
    conn: Any,
    ssh_client: Any,
    stop_event: Any,
    db_engine: str,
    server_mode: str = "direct",
) -> None:
    """
    Cierra la conexión según el motor y el modo de servidor.
    """
    if db_engine == "postgresql":
        from .db_utils_pg import (
            close_connection as pg_close,
            close_connection_direct as pg_close_direct,
        )
        if server_mode == "ssh":
            pg_close(conn, ssh_client, stop_event)
        else:
            pg_close_direct(conn, ssh_client, stop_event)
    else:
        from .db_utils import (
            close_connection as my_close,
            close_connection_direct as my_close_direct,
        )
        if server_mode == "ssh":
            my_close(conn, ssh_client, stop_event)
        else:
            my_close_direct(conn, ssh_client, stop_event)
