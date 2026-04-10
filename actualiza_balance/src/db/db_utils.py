import threading
import socket
import paramiko
import pymysql
import os
import warnings
from pathlib import Path

# Opcional: cargar variables desde .env si existe
try:
    from dotenv import load_dotenv

    # Carga .env desde el directorio del proyecto (o ajusta según tu estructura)
    BASE_DIR = Path(__file__).resolve().parent.parent.parent  # por ejemplo, carpeta raíz del proyecto
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # Si python-dotenv no está instalado, simplemente usamos las variables de entorno del sistema
    pass

# --- Silencia los DeprecationWarnings de TripleDES de cryptography/paramiko ---
warnings.filterwarnings(
    "ignore",
    message=".*TripleDES has been moved to cryptography.hazmat.decrepit.*",
    category=DeprecationWarning,
)

# ---------------------------
# CONFIGURACIÓN GLOBAL (desde variables de entorno)
# ---------------------------
SSH_HOST = os.getenv("DB_SSH_HOST", "127.0.0.1")
SSH_PORT = int(os.getenv("DB_SSH_PORT", "22"))
SSH_USER = os.getenv("DB_SSH_USER", "")
SSH_PASSWORD = os.getenv("DB_SSH_PASSWORD", "")

DB_HOST_REMOTE = os.getenv("DB_HOST_REMOTE", "127.0.0.1")
DB_PORT_REMOTE = int(os.getenv("DB_PORT_REMOTE", "3306"))
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "")


def _log(msg: str):
    """Log controlado por variable de entorno DB_UTILS_QUIET."""
    if os.getenv("DB_UTILS_QUIET") != "1":
        print(msg)


def _get_free_local_port() -> int:
    """Obtiene un puerto libre en 127.0.0.1 para el túnel local."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _pipe(src, dst, stop_event: threading.Event):
    """
    Copia datos entre 'src' y 'dst' hasta que alguno cierre o stop_event se active.
    Maneja EOFError/OSError cuando el canal SSH ya se cerró.
    """
    try:
        src.settimeout(1.0)
        while not stop_event.is_set():
            try:
                data = src.recv(32768)
            except (OSError, IOError):
                break
            if not data:
                break
            try:
                dst.sendall(data)
            except (EOFError, OSError, IOError):
                break
    except Exception:
        # Evita ruidos; este hilo es "best effort"
        pass
    finally:
        for sock in (src, dst):
            try:
                sock.close()
            except Exception:
                pass


def _forward_tunnel(local_port, remote_host, remote_port, transport, stop_event, threads_bucket):
    """
    Acepta conexiones locales y abre canales 'direct-tcpip' hacia (remote_host, remote_port)
    via 'transport'. Por cada par de sockets lanza 2 hilos _pipe (cliente->canal y canal->cliente).
    Guarda los hilos en 'threads_bucket' para poder hacer join en el cierre.
    """
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_sock.bind(("127.0.0.1", local_port))
        listen_sock.listen(100)
        listen_sock.settimeout(0.5)

        while not stop_event.is_set():
            try:
                client_sock, _ = listen_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                chan = transport.open_channel(
                    "direct-tcpip",
                    (remote_host, remote_port),
                    client_sock.getsockname(),
                )
            except Exception:
                try:
                    client_sock.close()
                except Exception:
                    pass
                continue

            # Dos hilos de pipe: client->chan y chan->client
            t1 = threading.Thread(target=_pipe, args=(client_sock, chan, stop_event), daemon=True)
            t2 = threading.Thread(target=_pipe, args=(chan, client_sock, stop_event), daemon=True)
            t1.start()
            t2.start()
            threads_bucket.append(t1)
            threads_bucket.append(t2)
    finally:
        try:
            listen_sock.close()
        except Exception:
            pass


def open_connection():
    """
    Abre túnel SSH y devuelve (conn, ssh_client, stop_event).
    Los hilos del túnel se guardan en ssh_client._dbutils_threads para cerrarlos luego.
    """
    # Validación mínima para que no te olvides de las variables
    if not SSH_HOST or not SSH_USER:
        raise RuntimeError("Faltan variables de entorno SSH (DB_SSH_HOST / DB_SSH_USER, etc.)")
    if not DB_USER or not DB_NAME:
        raise RuntimeError("Faltan variables de entorno de DB (DB_USER / DB_NAME, etc.).")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Conexión SSH
    client.connect(
        SSH_HOST,
        port=SSH_PORT,
        username=SSH_USER,
        password=SSH_PASSWORD,
        look_for_keys=False,
        allow_agent=False,
    )

    # Túnel
    transport = client.get_transport()
    local_port = _get_free_local_port()
    stop_event = threading.Event()

    # bucket para hilos de piping
    threads_bucket = []
    client._dbutils_threads = threads_bucket  # atributo "privado" ad-hoc

    threading.Thread(
        target=_forward_tunnel,
        args=(local_port, DB_HOST_REMOTE, DB_PORT_REMOTE, transport, stop_event, threads_bucket),
        daemon=True,
    ).start()

    # Conexión a MariaDB
    conn = pymysql.connect(
        host="127.0.0.1",
        port=local_port,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        local_infile=True,
    )

    _log(f"🔐 Conexión abierta: MariaDB ({DB_NAME}) a través de SSH ({SSH_HOST})")
    return conn, client, stop_event


def close_connection(conn, ssh_client, stop_event):
    """Cierra la conexión y el túnel SSH limpiamente (sin EOFError en hilos)."""
    # 1) Cierra conexión MariaDB
    try:
        if conn:
            conn.close()
            _log("✅ Conexión MariaDB cerrada.")
    except Exception as e:
        _log(f"⚠️ Error al cerrar MariaDB: {e}")

    # 2) Señala a los hilos que terminen y espera a que salgan
    try:
        if stop_event:
            stop_event.set()
        threads_bucket = getattr(ssh_client, "_dbutils_threads", None)
        if threads_bucket:
            for t in threads_bucket:
                try:
                    t.join(timeout=2.0)
                except Exception:
                    pass
    except Exception as e:
        _log(f"⚠️ Error al esperar hilos del túnel: {e}")

    # 3) Cierra el transporte/cliente SSH
    try:
        if ssh_client:
            try:
                transport = ssh_client.get_transport()
                if transport and transport.is_active():
                    transport.close()
            except Exception:
                pass
            ssh_client.close()
            _log("🔌 Túnel SSH cerrado.")
    except Exception as e:
        _log(f"⚠️ Error al cerrar túnel: {e}")


def open_connection_direct(
    host: str | None = None,
    port: int | None = None,
):
    """
    Conecta directo a MariaDB/MySQL sin túnel SSH.
    Útil cuando el código corre en el mismo host (o red) donde la BD es alcanzable.
    Devuelve conn.
    """
    # Defaults: usa las mismas vars que ya tienes
    host = host or DB_HOST_REMOTE
    port = port or DB_PORT_REMOTE

    if not host:
        raise RuntimeError("Falta host de DB (DB_HOST_REMOTE).")
    if not DB_USER or not DB_NAME:
        raise RuntimeError("Faltan variables de entorno de DB (DB_USER / DB_NAME, etc.).")

    conn = pymysql.connect(
        host=host,
        port=port,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        local_infile=True,
    )

    _log(f"🗄️ Conexión directa abierta: MariaDB ({DB_NAME}) en {host}:{port}")
    return conn, None, None  # para mantener la misma firma

def close_connection_direct(conn, ssh_client=None, stop_event=None):
    """Cierra una conexión directa a MariaDB/MySQL."""
    try:
        if conn:
            conn.close()
            _log("✅ Conexión MariaDB cerrada (directa).")
    except Exception as e:
        _log(f"⚠️ Error al cerrar MariaDB (directa): {e}")