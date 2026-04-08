# scripts/crea_base_staging.py
from pymysql.connections import Connection
from pymysql.cursors import Cursor
import time

def crea_staging(cx: Connection, cursor: Cursor) -> None:
    """
    Garantiza la existencia de la base de datos 'importar',
    utilizada en la etapa de staging.
    """

    print("Garantizando la existencia de la base de datos staging: importar ...")
    inicio = time.time()

    query = "CREATE DATABASE IF NOT EXISTS importar"
    cursor.execute(query)
    cx.commit()  # staging OK

    final = time.time()
    print("La existencia de la base de datos 'importar' está garantizada.")
    print(f"Tiempo transcurrido: {time.strftime('%H:%M:%S', time.gmtime(final - inicio))}.")
