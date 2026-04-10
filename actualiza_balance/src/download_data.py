# main_download.py
import zipfile
from .download.scraper import (
    descargar_balance_energia_plabacom,
    descargar_balance_sscc_plabacom
)
from pathlib import Path
from datetime import date
import io
import zipfile
from pathlib import Path
from datetime import date

def ejecutar_descarga(
    fecha_inicio: date,
    fecha_fin: date,
    workers: int,
    )-> None:
    # 1. Configuración de fechas
    fecha_inicio = fecha_inicio
    fecha_fin = fecha_fin

    # 2. Extraer año y mes para las rutas
    año = fecha_inicio.year
    mes = fecha_inicio.month

    # 3. Construcción del periodo (Ej: 2025 y 10 -> "2510")
    periodo = f"{str(año)[-2:]}{mes:02d}"

    # 4. Definición de rutas
    base_dir = Path(__file__).resolve().parent
    download_po_dir = base_dir / "data" / "raw" / "operacion" / str(año) / periodo / "zip"
    download_cmg_dir = base_dir / "data" / "raw" / "cmg_real" / str(año) / periodo / "zip"
    download_energia_dir = base_dir / "data" / "raw" / "energia" / str(año) / periodo / "zip"
    download_sscc_dir = base_dir / "data" / "raw" / "sscc" / str(año) / periodo / "zip"

    # Crear carpetas si no existen
    download_po_dir.mkdir(parents=True, exist_ok=True)
    download_cmg_dir.mkdir(parents=True, exist_ok=True)
    download_energia_dir.mkdir(parents=True, exist_ok=True)

    # Configuración de hilos (workers)
    workers = workers

    print(f"Iniciando descarga periodo {periodo} ({fecha_inicio} al {fecha_fin})...")

    # 7. Descarga balance energía desde Plabacom
    print(f"Iniciando descarga de balance de energía periodo {periodo} ({fecha_inicio} al {fecha_fin})...")
    descargar_balance_energia_plabacom(
        anio=año,
        mes=mes,
        carpeta=download_energia_dir,
    )
    print(f"Descarga de balance de energía finalizado. Archivos guardados en: {download_energia_dir}")

    # 8. Descargar archivos SSCC desde Plabacom
    print(f"Iniciando descarga de balance SSCC periodo {periodo} ({fecha_inicio} al {fecha_fin})...")
    descargar_balance_sscc_plabacom(
        anio=año,
        mes=mes,
        carpeta=download_sscc_dir,
    )

def extraer_po(    
    fecha_inicio: date,
    )-> None:
    # 1. Definición de rutas
    fecha_inicio = fecha_inicio
    año = fecha_inicio.year
    mes = fecha_inicio.month
    periodo = f"{str(año)[-2:]}{mes:02d}"

    base_dir = Path(__file__).resolve().parent
    download_dir = base_dir / "data" / "raw" / "operacion" / str(año) / periodo / "zip"
    raw_dir = base_dir / "data" / "raw" / "operacion" / str(año) / periodo

    # 2. Buscar archivos ZIP
    archivos_zip = list(download_dir.glob("*.zip"))

    if not archivos_zip:
        print(f"No se encontraron archivos ZIP en {download_dir}")
        return

    raw_dir.mkdir(parents=True, exist_ok=True)

    for archivo in archivos_zip:
        try:
            with zipfile.ZipFile(archivo, "r") as zip_ref:
                # 3. Filtrar archivos que comienzan con "PO"
                archivos_a_extraer = [f for f in zip_ref.namelist() if f.startswith("PO")]

                if not archivos_a_extraer:
                    print(f"No se encontraron archivos 'PO' dentro de {archivo.name}")
                    continue

                for file_to_extract in archivos_a_extraer:
                    print(f"Extrayendo {file_to_extract} desde {archivo.name}...")
                    zip_ref.extract(file_to_extract, path=raw_dir)

        except zipfile.BadZipFile:
            print(f"Error: El archivo {archivo.name} está corrupto.")
        except Exception as e:
            print(f"Ocurrió un error inesperado con {archivo.name}: {e}")

    print(f"Extracción selectiva completada en: {raw_dir}")

def extraer_cmg_real(
    fecha_inicio: date,
    base_dir: Path | None = None,
    overwrite: bool = False,
) -> None:
    """
    Extrae archivos contenidos en ZIPs anidados:
    - Recorre ZIPs en download_dir
    - Busca ZIPs internos dentro de cada ZIP externo
    - Abre el ZIP interno desde memoria (BytesIO) y extrae su contenido a raw_dir
    """
    # 1) Rutas
    anio = fecha_inicio.year
    mes = fecha_inicio.month
    periodo = f"{str(anio)[-2:]}{mes:02d}"

    if base_dir is None:
        base_dir = Path(__file__).resolve().parent

    download_dir = base_dir / "data" / "raw" / "cmg_real" / str(anio) / periodo / "zip"
    raw_dir = base_dir / "data" / "raw" / "cmg_real" / str(anio) / periodo

    archivos_zip = sorted(download_dir.glob("*.zip"))

    if not archivos_zip:
        print(f"No se encontraron archivos ZIP en {download_dir}")
        return

    raw_dir.mkdir(parents=True, exist_ok=True)

    extraidos_total = 0
    internos_total = 0

    for archivo in archivos_zip:
        try:
            with zipfile.ZipFile(archivo, "r") as outer_zip:
                internos = [n for n in outer_zip.namelist() if n.lower().endswith(".zip")]

                if not internos:
                    print(f"No se encontraron ZIPs internos dentro de {archivo.name}")
                    continue

                internos_total += len(internos)

                for inner_name in internos:
                    print(f"Extrayendo ZIP interno {inner_name} desde {archivo.name}...")

                    with outer_zip.open(inner_name) as inner_file:
                        inner_bytes = inner_file.read()

                    with zipfile.ZipFile(io.BytesIO(inner_bytes), "r") as inner_zip:
                        for member in inner_zip.infolist():
                            if member.is_dir():
                                continue

                            dest_path = raw_dir / member.filename

                            if dest_path.exists() and not overwrite:
                                continue

                            dest_path.parent.mkdir(parents=True, exist_ok=True)

                            with inner_zip.open(member, "r") as src, open(dest_path, "wb") as dst:
                                dst.write(src.read())

                            extraidos_total += 1

        except zipfile.BadZipFile:
            print(f"Error: El archivo {archivo.name} está corrupto o no es un ZIP válido.")
        except Exception as e:
            print(f"Ocurrió un error inesperado con {archivo.name}: {e}")

    print(f"ZIPs externos procesados: {len(archivos_zip)}")
    print(f"ZIPs internos encontrados: {internos_total}")
    print(f"Archivos extraídos: {extraidos_total}")
    print(f"Extracción de CMG REAL completada en: {raw_dir}")

def extraer_IT(
    fecha_inicio: date,
    base_dir: Path | None = None,
    overwrite: bool = False,
) -> None:
    """
    Extrae el archivo Asig_dev_IT_{periodo}_def.xlsm desde el ZIP de balance de energía (Plabacom).

    ZIP esperado en:
      data/raw/energia/{año}/{periodo}/zip/01 Resultados_{periodo}_BD01.zip

    Ruta interna esperada:
      01 Resultados_{periodo}_BD01/
        01 Balance de Energía/
          01 Asignacion Devolucion IT/
            Asig_dev_IT_{periodo}_def.xlsm

    Salida:
      data/raw/energia/{año}/{periodo}/Asig_dev_IT_{periodo}_def.xlsm
    """
    anio = fecha_inicio.year
    mes = fecha_inicio.month
    periodo = f"{str(anio)[-2:]}{mes:02d}"

    if base_dir is None:
        base_dir = Path(__file__).resolve().parent

    download_dir = base_dir / "data" / "raw" / "energia" / str(anio) / periodo / "zip"
    raw_dir = base_dir / "data" / "raw" / "energia" / str(anio) / periodo

    raw_dir.mkdir(parents=True, exist_ok=True)

    zip_name = f"01 Resultados_{periodo}_BD01.zip"
    zip_path = download_dir / zip_name

    inner_root = f"01 Resultados_{periodo}_BD01"
    inner_rel = (
        f"{inner_root}/01 Balance de Energía/"
        f"01 Asignacion Devolucion IT/"
        f"Asig_dev_IT_{periodo}_def.xlsm"
    )

    out_path = raw_dir / f"Asig_dev_IT_{periodo}_def.xlsm"
    if out_path.exists() and not overwrite:
        print(f"[INFO] Ya existe y overwrite=False, se omite: {out_path}")
        return

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            namelist = z.namelist()

            # 1) exact match
            candidates = [n for n in namelist if n == inner_rel]

            # 2) fallback: buscar por sufijo (por si cambia un poquito la carpeta intermedia)
            if not candidates:
                suffix = f"Asig_dev_IT_{periodo}_def.xlsm"
                candidates = [n for n in namelist if n.endswith(suffix)]

            if not candidates:
                near = [n for n in namelist if "Asig_dev_IT_" in n]
                print(f"[ERROR] No se encontró Asig_dev_IT_{periodo}_def.xlsm dentro de {zip_path.name}")
                if near:
                    print("[INFO] Rutas parecidas encontradas (primeras 15):")
                    for n in near[:15]:
                        print("  -", n)
                return

            inner_path = sorted(candidates, key=len, reverse=True)[0]

            with z.open(inner_path) as src, open(out_path, "wb") as dst:
                dst.write(src.read())

        print(f"[OK] Extraído IT -> {out_path}")

    except zipfile.BadZipFile:
        print(f"[ERROR] El ZIP está corrupto o no es válido: {zip_path}")
    except Exception as e:
        print(f"[ERROR] Ocurrió un error extrayendo IT desde {zip_path.name}: {e}")

def extrae_sobrecostos(
    fecha_inicio: date,
    base_dir: Path | None = None,
    overwrite: bool = False,
) -> None:
    """
    Extrae TODOS los archivos de sobrecostos diarios (xlsx) desde el ZIP de balance de energía (Plabacom)
    hacia la carpeta local "Detalles Diarios".

    ZIP esperado en:
      data/raw/energia/{año}/{periodo}/zip/01 Resultados_{periodo}_BD01.zip

    Carpeta interna (base) esperada (puede variar un poco, por eso hay fallback):
      01 Resultados_{periodo}_BD01/01 Balance de Energía/03 Sobrecostos/Detalles Diarios/

    Salida:
      data/raw/energia/{año}/{periodo}/Detalles Diarios/*.xlsx
    """
    import zipfile
    from pathlib import Path
    from datetime import date

    anio = fecha_inicio.year
    mes = fecha_inicio.month
    periodo = f"{str(anio)[-2:]}{mes:02d}"

    if base_dir is None:
        base_dir = Path(__file__).resolve().parent

    download_dir = base_dir / "data" / "raw" / "energia" / str(anio) / periodo / "zip"
    raw_dir = base_dir / "data" / "raw" / "energia" / str(anio) / periodo

    raw_dir.mkdir(parents=True, exist_ok=True)

    zip_name = f"01 Resultados_{periodo}_BD01.zip"
    zip_path = download_dir / zip_name

    if not zip_path.exists():
        candidatos = sorted(download_dir.glob(f"*{periodo}*BD01*.zip"))
        if len(candidatos) == 1:
            zip_path = candidatos[0]
        elif len(candidatos) > 1:
            print(f"[WARN] Hay múltiples candidatos de ZIP en {download_dir}. Usaré el más reciente.")
            zip_path = max(candidatos, key=lambda p: p.stat().st_mtime)
        else:
            print(f"[ERROR] No se encontró el ZIP de energía en: {download_dir}")
            print(f"        Esperado: {zip_name}")
            return

    # Carpeta destino local
    out_dir = raw_dir / "Detalles Diarios"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Prefijo interno "ideal"
    inner_root = f"01 Resultados_{periodo}_BD01"
    inner_base = f"{inner_root}/01 Balance de Energía/03 Sobrecostos/Detalles Diarios/"

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            namelist = z.namelist()

            # 1) tomar todos los xlsx bajo el prefijo esperado
            candidates = [
                n for n in namelist
                if n.startswith(inner_base) and n.lower().endswith(".xlsx")
            ]

            # 2) fallback: si cambió el root o carpeta, buscar cualquier ruta que contenga "03 Sobrecostos"
            #    y "Detalles Diarios" y que termine en .xlsx
            if not candidates:
                candidates = [
                    n for n in namelist
                    if ("03 Sobrecostos" in n or "03%20Sobrecostos" in n)  # por si viene encodeado (raro en zip)
                    and ("Detalles Diarios" in n)
                    and n.lower().endswith(".xlsx")
                ]

            # 3) fallback extra: cualquier xlsx que contenga "Detalles Diarios"
            if not candidates:
                candidates = [
                    n for n in namelist
                    if ("Detalles Diarios" in n) and n.lower().endswith(".xlsx")
                ]

            if not candidates:
                near = [n for n in namelist if "Sobrecostos" in n or "Detalles Diarios" in n]
                print(f"[ERROR] No se encontraron xlsx de sobrecostos diarios dentro de {zip_path.name}")
                if near:
                    print("[INFO] Rutas parecidas encontradas (primeras 30):")
                    for n in near[:30]:
                        print("  -", n)
                return

            extraidos = 0
            omitidos = 0

            for inner_path in sorted(candidates):
                # Mantener el nombre de archivo final (sin carpetas)
                fname = Path(inner_path).name
                dest = out_dir / fname

                if dest.exists() and not overwrite:
                    omitidos += 1
                    continue

                # Extraer por stream
                dest.parent.mkdir(parents=True, exist_ok=True)
                with z.open(inner_path) as src, open(dest, "wb") as dst:
                    dst.write(src.read())

                extraidos += 1

            print(f"[OK] Sobrecostos diarios -> {out_dir}")
            print(f"     xlsx encontrados: {len(candidates)} | Extraídos: {extraidos} | Omitidos: {omitidos} | overwrite={overwrite}")

    except zipfile.BadZipFile:
        print(f"[ERROR] El ZIP está corrupto o no es válido: {zip_path}")
    except Exception as e:
        print(f"[ERROR] Ocurrió un error extrayendo sobrecostos diarios desde {zip_path.name}: {e}")    

def extra_cmg_balance(
    fecha_inicio: date,
    base_dir: Path | None = None,
    overwrite: bool = False,)-> None:
    """
    Extrae el archivo cmg{periodo}_15min_formateado.csv desde el ZIP de balance de energía (Plabacom).

    ZIP esperado en:
      data/raw/energia/{año}/{periodo}/zip/03 Bases de Datos_{periodo}_BD01.zip

    Ruta interna esperada:
      03 Bases de Datos_{periodo}_BD01/
        01 Cmg/
            cmg{periodo}_15min_formateado.csv

    Salida:
      data/raw/cmg/{año}/{periodo}/cmg{periodo}_15min_formateado.csv
    """

    anio = fecha_inicio.year
    mes = fecha_inicio.month
    periodo = f"{str(anio)[-2:]}{mes:02d}"

    if base_dir is None:
        base_dir = Path(__file__).resolve().parent

    download_dir = base_dir / "data" / "raw" / "energia" / str(anio) / periodo / "zip"
    raw_dir = base_dir / "data" / "raw" / "cmg" / str(anio) / periodo

    raw_dir.mkdir(parents=True, exist_ok=True)

    zip_name = f"03 Bases de Datos_{periodo}_BD01.zip"
    zip_path = download_dir / zip_name

    inner_root = f"03 Bases de Datos_{periodo}_BD01"
    inner_rel = (
        f"{inner_root}/03 Bases de Datos_{periodo}_BD01/"
        f"01 Cmg/"
        f"cmg{periodo}_15min_formateado.csv"
    )

    out_path = raw_dir / f"cmg{periodo}_15min_formateado.csv"
    if out_path.exists() and not overwrite:
        print(f"[INFO] Ya existe y overwrite=False, se omite: {out_path}")
        return

    try:
            with zipfile.ZipFile(zip_path, "r") as z:
                namelist = z.namelist()

                # 1) exact match
                candidates = [n for n in namelist if n == inner_rel]

                # 2) fallback: buscar por sufijo (por si cambia un poquito la carpeta intermedia)
                if not candidates:
                    suffix = f"cmg{periodo}_15min_formateado.csv"
                    candidates = [n for n in namelist if n.endswith(suffix)]

                if not candidates:
                    near = [n for n in namelist if "cmg" in n]
                    print(f"[ERROR] No se encontró cmg{periodo}_15min_formateado.csv dentro de {zip_path.name}")
                    if near:
                        print("[INFO] Rutas parecidas encontradas (primeras 15):")
                        for n in near[:15]:
                            print("  -", n)
                    return

                inner_path = sorted(candidates, key=len, reverse=True)[0]

                with z.open(inner_path) as src, open(out_path, "wb") as dst:
                    dst.write(src.read())

            print(f"[OK] Extraído cmg balance -> {out_path}")

    except zipfile.BadZipFile:
        print(f"[ERROR] El ZIP está corrupto o no es válido: {zip_path}")
    except Exception as e:
        print(f"[ERROR] Ocurrió un error extrayendo cmg desde {zip_path.name}: {e}")

def extrae_barras(
    fecha_inicio: date,
    base_dir: Path | None = None,
    overwrite: bool = False,
) -> None:
    """
    Extrae el/los archivos Barras_export_*.xlsx desde el ZIP de balance de energía (Plabacom).
    """

    anio = fecha_inicio.year
    mes = fecha_inicio.month
    periodo = f"{str(anio)[-2:]}{mes:02d}"

    if base_dir is None:
        base_dir = Path(__file__).resolve().parent

    download_dir = base_dir / "data" / "raw" / "energia" / str(anio) / periodo / "zip"
    raw_dir = base_dir / "data" / "raw" / "energia" / str(anio) / periodo
    raw_dir.mkdir(parents=True, exist_ok=True)

    zip_name = f"02 Antecedentes de Cálculo_{periodo}_BD01.zip"
    zip_path = download_dir / zip_name

    if not zip_path.exists():
        print(f"[ERROR] No existe el ZIP esperado: {zip_path}")
        return

    inner_root = f"02 Antecedentes de Cálculo_{periodo}_BD01"
    inner_dir = (
        f"{inner_root}/"
        f"01 Balance Físico/"
        f"01 Balance Transmisión/"
    )

    
    target_ext = ".xlsx"   

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            namelist = z.namelist()

            # ✅ buscar archivos dentro del directorio esperado
            candidates = []
            for n in namelist:
                if not n.startswith(inner_dir):
                    continue
                base = Path(n).name
                if base.startswith("Barras_export_") and base.lower().endswith(target_ext):
                    candidates.append(n)

            # ✅ fallback: buscar en cualquier parte del ZIP por nombre
            if not candidates:
                for n in namelist:
                    base = Path(n).name
                    if base.startswith("Barras_export_") and base.lower().endswith(target_ext):
                        candidates.append(n)

            if not candidates:
                near = [n for n in namelist if "Barras" in n or "barras" in n.lower()]
                print(f"[ERROR] No se encontró Barras_export_*{target_ext} dentro de {zip_path.name}")
                if near:
                    print("[INFO] Rutas parecidas encontradas (primeras 15):")
                    for n in near[:15]:
                        print("  -", n)
                return

            # Si hay varios, extrae todos (más útil que solo uno)
            extraidos = 0
            for inner_path in sorted(candidates, key=len, reverse=True):
                out_path = raw_dir / Path(inner_path).name

                if out_path.exists() and not overwrite:
                    print(f"[INFO] Ya existe y overwrite=False, se omite: {out_path}")
                    continue

                with z.open(inner_path) as src, open(out_path, "wb") as dst:
                    dst.write(src.read())

                extraidos += 1
                print(f"[OK] Extraído -> {out_path}")

            if extraidos == 0:
                print("[INFO] No se extrajo nada (todos existían y overwrite=False).")

    except zipfile.BadZipFile:
        print(f"[ERROR] El ZIP está corrupto o no es válido: {zip_path}")
    except Exception as e:
        print(f"[ERROR] Ocurrió un error extrayendo Barras_export_*{target_ext} desde {zip_path.name}: {e}")

def extrae_valorizado_pncp(
    fecha_inicio: date,
    base_dir: Path | None = None,
    overwrite: bool = False,
    ) -> None:
    """
    Extrae el archivo Reconstruye_valorizado_pncp_pe_{periodo}D.xlsx desde el ZIP de balance de energía (Plabacom).

    ZIP esperado en:
      data/raw/energia/{año}/{periodo}/zip/02 Antecedentes de Cálculo_{periodo}_BD01.zip

    Ruta interna esperada:
      02 Antecedentes de Cálculo_{periodo}_BD01/
        02 Antecedentes de Cálculo_{periodo}_BD01/
          07 Precio Estabilizado/
              Reconstruye_valorizado_pnpc_pe_{periodo}D.xlsx

    Salida:
      data/raw/energia/{año}/{periodo}/Reconstruye_valorizado_pnpc_pe_{periodo}D.xlsx
    """

    anio = fecha_inicio.year
    mes = fecha_inicio.month
    periodo = f"{str(anio)[-2:]}{mes:02d}"

    if base_dir is None:
        base_dir = Path(__file__).resolve().parent

    download_dir = base_dir / "data" / "raw" / "energia" / str(anio) / periodo / "zip"
    raw_dir = base_dir / "data" / "raw" / "energia" / str(anio) / periodo

    raw_dir.mkdir(parents=True, exist_ok=True)

    zip_name = f"02 Antecedentes de Cálculo_{periodo}_BD01.zip"
    zip_path = download_dir / zip_name

    inner_root = f"02 Antecedentes de Cálculo_{periodo}_BD01"
    inner_rel = (
        f"{inner_root}/02 Antecedentes de Cálculo_{periodo}_BD01/"
        f"07 Precio Estabilizado/"
        f"Reconstruye_valorizado_pnpc_pe_{periodo}D.xlsx"
    )

    out_path = raw_dir / f"Reconstruye_valorizado_pnpc_pe_{periodo}D.xlsx"
    if out_path.exists() and not overwrite:
        print(f"[INFO] Ya existe y overwrite=False, se omite: {out_path}")
        return

    try:
            with zipfile.ZipFile(zip_path, "r") as z:
                namelist = z.namelist()

                # 1) exact match
                candidates = [n for n in namelist if n == inner_rel]

                # 2) fallback: buscar por sufijo (por si cambia un poquito la carpeta intermedia)
                if not candidates:
                    suffix = f"Reconstruye_valorizado_pnpc_pe_{periodo}D.xlsx"
                    candidates = [n for n in namelist if n.endswith(suffix)]

                if not candidates:
                    near = [n for n in namelist if "Reconstruye_valorizado_pnpc_pe" in n]
                    print(f"[ERROR] No se encontró Reconstruye_valorizado_pnpc_pe_{periodo}D.xlsx dentro de {zip_path.name}")
                    if near:
                        print("[INFO] Rutas parecidas encontradas (primeras 15):")
                        for n in near[:15]:
                            print("  -", n)
                    return

                inner_path = sorted(candidates, key=len, reverse=True)[0]

                with z.open(inner_path) as src, open(out_path, "wb") as dst:
                    dst.write(src.read())

            print(f"[OK] Extraído valorizado pncp -> {out_path}")

    except zipfile.BadZipFile:
        print(f"[ERROR] El ZIP está corrupto o no es válido: {zip_path}")
    except Exception as e:
        print(f"[ERROR] Ocurrió un error extrayendo valorizado pncp desde {zip_path.name}: {e}")

def extra_medidas_valorizadas(
    fecha_inicio: date,
    base_dir: Path | None = None,
    overwrite: bool = False,
) -> None:
    """
    Extrae el CONTENIDO de los archivos .zip internos de "02 Medidas por tipo"
    desde el ZIP 03 Bases de Datos_{periodo}_BD01 (Plabacom).

    ZIP esperado en:
      data/raw/energia/{año}/{periodo}/zip/03 Bases de Datos_{periodo}_BD01.zip

    Rutas internas esperada (carpeta):
      .../02 Medidas por tipo/*.zip

    Salida (contenido descomprimido):
      data/raw/energia/{año}/{periodo}/  (directo aquí)
    """
    # 1) Rutas
    anio = fecha_inicio.year
    mes = fecha_inicio.month
    periodo = f"{str(anio)[-2:]}{mes:02d}"

    if base_dir is None:
        base_dir = Path(__file__).resolve().parent

    download_dir = base_dir / "data" / "raw" / "energia" / str(anio) / periodo / "zip"
    raw_dir = base_dir / "data" / "raw" / "energia" / str(anio) / periodo
    raw_dir.mkdir(parents=True, exist_ok=True)

    zip_name = f"03 Bases de Datos_{periodo}_BD01.zip"
    zip_path = download_dir / zip_name

    if not zip_path.exists():
        print(f"[ERROR] No se encontró el ZIP de energía en: {download_dir}")
        print(f"        Esperado: {zip_name}")
        return

    # buscamos cualquier ruta que contenga esta carpeta
    target_folder = "02 Medidas por tipo/"

    extraidos_total = 0
    internos_total = 0

    try:
        with zipfile.ZipFile(zip_path, "r") as outer_zip:
            namelist = outer_zip.namelist()

            # ZIPs internos SOLO dentro de "02 Medidas por tipo/"
            internos = [
                n for n in namelist
                if n.lower().endswith(".zip") and (target_folder.lower() in n.lower())
            ]

            if not internos:
                print(f"[ERROR] No se encontraron ZIPs internos en '{target_folder}' dentro de {zip_path.name}")
                near = [n for n in namelist if "medidas" in n.lower()]
                if near:
                    print("[INFO] Rutas parecidas (primeras 20):")
                    for n in near[:20]:
                        print("  -", n)
                return

            internos_total = len(internos)

            for inner_name in sorted(internos):
                inner_zip_filename = Path(inner_name).name
                print(f"[INFO] Procesando ZIP interno: {inner_zip_filename}")

                # leer bytes del zip interno
                with outer_zip.open(inner_name) as inner_file:
                    inner_bytes = inner_file.read()

                # abrir zip interno desde memoria y extraer contenido a raw_dir
                with zipfile.ZipFile(io.BytesIO(inner_bytes), "r") as inner_zip:
                    for member in inner_zip.infolist():
                        if member.is_dir():
                            continue

                        dest_path = raw_dir / member.filename

                        if dest_path.exists() and not overwrite:
                            continue

                        dest_path.parent.mkdir(parents=True, exist_ok=True)

                        with inner_zip.open(member, "r") as src, open(dest_path, "wb") as dst:
                            dst.write(src.read())

                        extraidos_total += 1

    except zipfile.BadZipFile:
        print(f"[ERROR] El archivo {zip_path.name} está corrupto o no es un ZIP válido.")
        return
    except Exception as e:
        print(f"[ERROR] Ocurrió un error inesperado con {zip_path.name}: {e}")
        return

    print(f"[OK] ZIP externo procesado: 1 ({zip_path.name})")
    print(f"[OK] ZIPs internos encontrados (02 Medidas por tipo): {internos_total}")
    print(f"[OK] Archivos extraídos desde ZIPs internos: {extraidos_total}")
    print(f"[OK] Extracción completada en: {raw_dir}")

def extrae_inyecciones_valorizadas(
    fecha_inicio: date,
    base_dir: Path | None = None,
    overwrite: bool = False,
) -> None:
    """
    Extrae TODOS los archivos contenidos en la carpeta
    "04 Precio Estabilizado PNCP" desde el ZIP
    "03 Bases de Datos_{periodo}_BD01.zip" del balance de energía (Plabacom).

    ZIP esperado:
      data/raw/energia/{año}/{periodo}/zip/03 Bases de Datos_{periodo}_BD01.zip

    Carpeta interna esperada:
      03 Bases de Datos_{periodo}_BD01/04 Precio Estabilizado PNCP/

    Salida:
      data/raw/energia/{año}/{periodo}/  (SIN subcarpetas)
    """

    anio = fecha_inicio.year
    mes = fecha_inicio.month
    periodo = f"{str(anio)[-2:]}{mes:02d}"

    if base_dir is None:
        base_dir = Path(__file__).resolve().parent

    download_dir = base_dir / "data" / "raw" / "energia" / str(anio) / periodo / "zip"
    raw_dir = base_dir / "data" / "raw" / "energia" / str(anio) / periodo
    raw_dir.mkdir(parents=True, exist_ok=True)

    zip_name = f"03 Bases de Datos_{periodo}_BD01.zip"
    zip_path = download_dir / zip_name

    if not zip_path.exists():
        print(f"[ERROR] No existe el ZIP esperado: {zip_path}")
        return

    inner_root = f"03 Bases de Datos_{periodo}_BD01"
    inner_dir = f"{inner_root}/04 Precio Estabilizado PNCP/"

    extraidos = 0
    omitidos = 0

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            namelist = z.namelist()

            # 1) candidatos dentro del directorio esperado (archivos, no carpetas)
            candidates = [
                n for n in namelist
                if n.startswith(inner_dir) and not n.endswith("/")
            ]

            # 2) fallback: por si cambia el root y existe igual la carpeta
            if not candidates:
                candidates = [
                    n for n in namelist
                    if ("04 Precio Estabilizado PNCP/" in n) and (not n.endswith("/"))
                ]

            if not candidates:
                near = [n for n in namelist if "precio estabilizado" in n.lower() or "pncp" in n.lower()]
                print(f"[ERROR] No se encontraron archivos dentro de '04 Precio Estabilizado PNCP' en {zip_path.name}")
                if near:
                    print("[INFO] Rutas parecidas (primeras 20):")
                    for n in near[:20]:
                        print("  -", n)
                return

            # ✅ Flatten: sacar solo el nombre del archivo y guardarlo directo en raw_dir
            for inner_path in sorted(candidates):
                out_path = raw_dir / Path(inner_path).name

                if out_path.exists() and not overwrite:
                    omitidos += 1
                    continue

                with z.open(inner_path) as src, open(out_path, "wb") as dst:
                    dst.write(src.read())

                extraidos += 1

    except zipfile.BadZipFile:
        print(f"[ERROR] El ZIP está corrupto o no es válido: {zip_path}")
        return
    except Exception as e:
        print(f"[ERROR] Ocurrió un error extrayendo '04 Precio Estabilizado PNCP' desde {zip_path.name}: {e}")
        return

    print(f"[OK] Archivos extraídos: {extraidos}")
    if omitidos:
        print(f"[INFO] Omitidos por existir (overwrite=False): {omitidos}")
    print(f"[OK] Extracción completada en: {raw_dir}")

def extrae_sscc(
    fecha_inicio: date,
    base_dir: Path | None = None,
    overwrite: bool = False,
) -> None:
    """
    Extrae el archivo 1_CUADROS_PAGO_SSCC_{periodo}_def.xlsm desde el ZIP de balance de SSCC (Plabacom).

    ZIP esperado en:
      data/raw/sscc/{año}/{periodo}/zip/*.zip  (se busca por patrón si no calza exacto)

    Salida:
      data/raw/sscc/{año}/{periodo}/1_CUADROS_PAGO_SSCC_{periodo}_def.xlsm
    """

    anio = fecha_inicio.year
    mes = fecha_inicio.month
    periodo = f"{str(anio)[-2:]}{mes:02d}"

    if base_dir is None:
        base_dir = Path(__file__).resolve().parent

    # ✅ corregido: sscc (no "ene")
    download_dir = base_dir / "data" / "raw" / "sscc" / str(anio) / periodo / "zip"
    raw_dir = base_dir / "data" / "raw" / "sscc" / str(anio) / periodo
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Nombre del archivo objetivo dentro del ZIP
    target_name = f"1_CUADROS_PAGO_SSCC_{periodo}_def.xlsm"
    out_path = raw_dir / target_name

    if out_path.exists() and not overwrite:
        print(f"[INFO] Ya existe y overwrite=False, se omite: {out_path}")
        return

    # ✅ no asumas un zip_name exacto: busca candidatos
    if not download_dir.exists():
        print(f"[ERROR] No existe la carpeta de descarga: {download_dir}")
        return

    candidatos = sorted(download_dir.glob("*.zip"))
    if not candidatos:
        print(f"[ERROR] No se encontraron ZIPs en: {download_dir}")
        return

    # Si hay muchos, prioriza el que contenga "SSCC" y el periodo, si no el más reciente
    preferidos = [p for p in candidatos if ("SSCC" in p.name.upper() and periodo in p.name)]
    zip_path = max(preferidos, key=lambda p: p.stat().st_mtime) if preferidos else max(candidatos, key=lambda p: p.stat().st_mtime)

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            namelist = z.namelist()

            # 1) match directo por nombre base (sin importar carpetas internas)
            candidates = [n for n in namelist if Path(n).name == target_name]

            # 2) fallback: por sufijo (por si viene con subcarpetas)
            if not candidates:
                candidates = [n for n in namelist if n.endswith(target_name)]

            if not candidates:
                near = [n for n in namelist if "CUADROS_PAGO_SSCC" in n]
                print(f"[ERROR] No se encontró {target_name} dentro de {zip_path.name}")
                if near:
                    print("[INFO] Rutas parecidas encontradas (primeras 15):")
                    for n in near[:15]:
                        print("  -", n)
                return

            inner_path = sorted(candidates, key=len, reverse=True)[0]

            with z.open(inner_path) as src, open(out_path, "wb") as dst:
                dst.write(src.read())

        print(f"[OK] Extraído valorizado SSCC -> {out_path}")

    except zipfile.BadZipFile:
        print(f"[ERROR] El ZIP está corrupto o no es válido: {zip_path}")
    except Exception as e:
        print(f"[ERROR] Ocurrió un error extrayendo valorizado SSCC desde {zip_path.name}: {e}")

def download_data(fecha_inicio: date, fecha_fin: date, workers: int):
    ejecutar_descarga(fecha_inicio, fecha_fin, workers)
    extraer_po(fecha_inicio, fecha_fin)
    extraer_cmg_real(fecha_inicio, fecha_fin)
    extraer_IT(fecha_inicio, fecha_fin)
    extrae_sobrecostos(fecha_inicio, fecha_fin)
    extra_cmg_balance(fecha_inicio, fecha_fin )
    extrae_barras(fecha_inicio)
    extrae_valorizado_pncp(fecha_inicio)
    extra_medidas_valorizadas(fecha_inicio)
    extrae_inyecciones_valorizadas(fecha_inicio)
    extrae_sscc(fecha_inicio)

'''
if __name__ == "download_data":
    fecha_inicio = date(2025, 10, 1)
    fecha_fin = date(2025, 10, 31)
    download_data(fecha_inicio, fecha_fin, workers=4)
'''