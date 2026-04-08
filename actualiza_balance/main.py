import json
import logging
from pathlib import Path
from datetime import date
from download_data import download_data
from carga_bd import carga_bd

def load_config(config_path: str = "config.json") -> dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

if __name__ == "__main__":
    # Configuración de logging
    logging.basicConfig(
        level=logging.INFO,  
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    config = load_config()
    fecha_inicio = date.fromisoformat(config["fecha_inicio"])
    fecha_fin = date.fromisoformat(config["fecha_fin"])
    workers = config.get("workers", 4)
    server_mode = config.get("server_mode", "direct")
    dry_run = config.get("dry_run", True)
    part1_exec = config.get("part1_exec", False)
    part2_exec = config.get("part2_exec", False)
    tipo = config.get("tipo", "Definitivo")
    download = config.get("download", False)
    carga = config.get("carga", False)

    if download:
        logging.info("Iniciando descarga de datos...")
        download_data(fecha_inicio, fecha_fin, workers)

    if carga:
        logging.info("Iniciando carga a base de datos...")
        carga_bd(
            fecha_inicio=fecha_inicio,
            tipo=tipo,
            mode="skip",
            server_mode=server_mode,
            dry_run=dry_run,
            part1_exec=part1_exec,
            part2_exec=part2_exec
        )
