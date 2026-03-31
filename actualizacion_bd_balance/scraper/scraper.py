#!/usr/bin/env python3
from __future__ import annotations

# --- stdlib ---
import os, sys
from datetime import datetime, date, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote, unquote, urlparse
from calendar import monthrange

# --- terceros ---
import requests

"""
Descargador KISS:
- Balance de energía (PLABACOM/S3)
- Vertimientos (wp-content)
- CMG Real (wp-content, por día)  ✅ (resuelve carpeta YYYY/MM por día: mes actual o siguientes)
- Costos Variables (wp-content, por día)
- Políticas de Operación (PROGRAMA..., por día) con variantes -3/-2/-1

Estrategia:
1) Construir URL determinística.
2) Intentar con requests (Session + headers, referer).
3) Si coordinador.cl devuelve 403 en el bloque → abrir UN solo Chrome y bajar TODO el bloque.

Nota importante:
- Para PROGRAMA...-k.zip, coordinador.cl suele responder 403 tanto si existe como si no existe,
  por lo que NO podemos decidir existencia con status. Se resuelve el “índice” usando Chrome
  (una sola ventana) antes de descargar el bloque.
"""

# ======================================================
# UTF-8 seguro y logs simples
# ======================================================
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _utf8_capable() -> bool:
    enc = (getattr(sys.stdout, "encoding", None) or "").lower()
    return "utf" in enc


def log_info(msg: str):
    prefix = "[✔ INFO]" if _utf8_capable() else "[INFO]"
    print(f"{prefix} {msg}")


def log_warn(msg: str):
    prefix = "[⚠ WARN]" if _utf8_capable() else "[WARN]"
    print(f"{prefix} {msg}")


def log_error(msg: str):
    prefix = "[✖ ERROR]" if _utf8_capable() else "[ERROR]"
    print(f"{prefix} {msg}")


ARCHIVOS_NO_ENCONTRADOS: list[str] = []

# ======================================================
# Constantes
# ======================================================
MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def _carpeta_mes(mes: int | str) -> str:
    if isinstance(mes, str):
        mes = int(mes)
    return f"{mes:02d}_{MESES_ES[mes]}"


# ======================================================
# Headers tipo navegador + utilidades
# ======================================================
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/zip,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/octet-stream,*/*",
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Referer": "https://www.coordinador.cl/",
}


def _normalize_coordinador_host(url: str) -> str:
    """Fuerza www.coordinador.cl (evita www2 o host sin www)."""
    try:
        p = urlparse(url)
        host = p.netloc
        new = url
        if host.startswith("www2.coordinador.cl"):
            new = url.replace("://www2.coordinador.cl", "://www.coordinador.cl", 1)
        elif host == "coordinador.cl":
            new = url.replace("://coordinador.cl", "://www.coordinador.cl", 1)
        return new
    except Exception:
        return url


def _coordinador_variants(url: str) -> list[str]:
    """No genera variantes; normaliza a www y retorna una sola opción (KISS)."""
    return [_normalize_coordinador_host(url)]


def _dir_referer(url: str) -> str:
    """Devuelve la carpeta del recurso como Referer."""
    try:
        p = urlparse(url)
        dir_path = "/".join(p.path.split("/")[:-1]) + "/"
        return f"{p.scheme}://{p.netloc}{dir_path}"
    except Exception:
        return "https://www.coordinador.cl/"


def _probe_ok(url: str, timeout: int = 12) -> bool:
    """Prueba existencia con GET parcial (solo si el server soporta Range). Útil para ZIP en S3/WordPress."""
    try:
        with requests.Session() as s:
            s.headers.update(BROWSER_HEADERS)
            r = s.get(url, headers={"Range": "bytes=0-0"}, timeout=timeout, stream=True)
            return r.status_code in (200, 206)
    except Exception:
        return False


def _exists_simple_get(url: str, timeout: int = 12) -> bool:
    """Probar existencia sin Range (útil para .xlsx) con headers y referer."""
    try:
        with requests.Session() as s:
            s.headers.update(BROWSER_HEADERS)
            hdrs = {}
            if "coordinador.cl" in url:
                hdrs["Referer"] = _dir_referer(url)
                s.get("https://www.coordinador.cl/", timeout=8, allow_redirects=True)
            r = s.get(_normalize_coordinador_host(url), timeout=timeout, stream=True, allow_redirects=True, headers=hdrs)
            return r.status_code == 200
    except Exception:
        return False


def _first_status(url: str, timeout: int = 20) -> int | None:
    """Obtiene un status de forma rápida para decidir estrategia del BLOQUE."""
    try:
        with requests.Session() as s:
            s.headers.update(BROWSER_HEADERS)
            hdrs = {}
            if "coordinador.cl" in url:
                hdrs["Referer"] = _dir_referer(url)
                s.get("https://www.coordinador.cl/", timeout=10, allow_redirects=True)
                r = s.get(_normalize_coordinador_host(url), headers=hdrs, timeout=timeout, stream=True)
            else:
                r = s.get(url, headers={"Range": "bytes=0-0"}, timeout=timeout, stream=True)
            return r.status_code
    except Exception:
        return None


# ======================================================
# CMG: resolver carpeta correcta (YYYY/MM) por DÍA
#   - El nombre del archivo usa el día real (yymmdd) siempre
#   - La carpeta puede estar en el mismo mes o meses siguientes (shift +1, +2...)
#   - 403 se considera "EXISTE" (coordinador puede proteger archivos existentes)
# ======================================================
def _add_months(d: date, delta: int) -> date:
    """
    Suma delta meses a una fecha.
    Mantiene el día si existe; si no, recorta al último día del mes resultante.
    """
    y = d.year
    m = d.month + delta
    y += (m - 1) // 12
    m = ((m - 1) % 12) + 1
    last = monthrange(y, m)[1]
    return date(y, m, min(d.day, last))


def _cmg_url_for_shift(d: date, month_shift: int, base="https://www.coordinador.cl/wp-content/uploads") -> str:
    """
    Construye URL CMG para el día d, probando carpeta desplazada por month_shift meses.
    """
    folder = _add_months(d, month_shift)
    ymd_short = d.strftime("%y%m%d")
    url = f"{base}/{folder:%Y/%m}/Antecedentes_CMG_Real_def_{ymd_short}.zip"
    return _normalize_coordinador_host(url)


def resolver_cmg_url_con_browser_por_dia(
    br: "_BrowserSession",
    d: date,
    base="https://www.coordinador.cl/wp-content/uploads",
    max_shift: int = 2,
) -> str:
    """
    Prueba shift+0..shift+max_shift y retorna la primera URL que "existe".
    Existencia:
      - 2xx/3xx => existe
      - 403     => existe (protegido)
    """
    for k in range(0, max_shift + 1):
        u = _cmg_url_for_shift(d, month_shift=k, base=base)
        carpeta = "/".join(u.split("/")[-3:-1])  # YYYY/MM
        nombre = u.split("/")[-1]
        st = br.probe_status_head(u, timeout=20)
        log_info(f"[resolve+chrome][cmg-day] {d} probando shift+{k} ({carpeta}) st={st} :: {nombre}")
        if st is not None and ((200 <= st < 400) or st == 403):
            log_info(f"[resolve+chrome][cmg-day] {d} ELEGIDA shift+{k} ({carpeta}) st={st}")
            return u

    fallback = _cmg_url_for_shift(d, month_shift=0, base=base)
    log_warn(f"[resolve+chrome][cmg-day] {d} ninguna carpeta dio 2xx/3xx/403; usando fallback: {fallback}")
    return fallback


# ======================================================
# Balance de energía (PLABACOM)
# ======================================================
PREFIJOS_BALANCE = ["01 Resultados", "02 Antecedentes de Cálculo", "03 Bases de Datos"]


def nombre_archivo_transferencias_economicas(prefijo: str, fecha: str, codigo: str = "BD01", ext: str = "zip"):
    return f"{prefijo}_{fecha}_{codigo}.{ext}"


def construye_plabacom_url(
    nombre_archivo: str,
    anio: int,
    mes: int | str,
    categoria="Energia",
    estado="Definitivo",
    version="v_1",
    base="https://cen-plabacom.s3.amazonaws.com",
) -> str:
    carpeta_mes = _carpeta_mes(mes)
    path = f"PLABACOM/{anio}/{carpeta_mes}/{categoria}/{estado}/{version}/{nombre_archivo}"
    return f"{base}/{quote(path, safe='/')}"


def encontrar_mes_disponible_te(anio: int, mes: int, max_retro: int = 12) -> tuple[int, int] | None:
    """Busca hacia atrás hasta 12 meses un mes que tenga '01 Resultados' disponible en S3."""
    for _ in range(max_retro):
        cod_fecha = f"{str(anio)[-2:]}{mes:02d}"
        probe = nombre_archivo_transferencias_economicas("01 Resultados", cod_fecha)
        url = construye_plabacom_url(probe, anio, mes)
        if _probe_ok(url):  # S3 ZIP suele soportar Range/206
            return anio, mes
        anio, mes = ((anio - 1, 12) if mes == 1 else (anio, mes - 1))
    return None


# ======================================================
# Balance de SSSCC (PLABACOM)
# ======================================================

PREFIJOS_SSCC= "Balance_SSCC"

def nombre_archivo_sscc(prefijo: str, fecha: date, codigo: str ="def", ext: str = "zip"):
    anio = fecha.year
    nombre_mes_abreviado = fecha.strftime("%b")
    nombre_mes_abreviado=nombre_mes_abreviado.lower()
    return f"{prefijo}_{anio}_{nombre_mes_abreviado}_{codigo}.{ext}"

def construye_plabacom_url_sscc(
    nombre_archivo: str,
    anio: int,
    mes: int | str,
    categoria="SSCC",
    estado="Definitivo",
    version="v_1",
    base="https://cen-plabacom.s3.amazonaws.com",
) -> str:
    carpeta_mes = _carpeta_mes(mes)
    path = f"PLABACOM/{anio}/{carpeta_mes}/{categoria}/{estado}/{version}/{nombre_archivo}"
    return f"{base}/{quote(path, safe='/')}"

# ======================================================
# Vertimientos
# ======================================================
def construye_vertimientos_url(
    anio: int,
    mes: int | str,
    estado_sufijo="-PE-PFV_Publicar",
    base="https://www.coordinador.cl/wp-content/uploads",
) -> str:
    if isinstance(mes, str):
        mes = int(mes)
    yy = f"{anio % 100:02d}"
    mm = f"{mes:02d}"
    nombre_mes = MESES_ES[mes]
    filename = f"Reducciones-de-Energia-Eolica-Solar-Hidro-en-el-SEN_{nombre_mes}-{yy}{estado_sufijo}.xlsx"
    path = f"{anio}/{mm}/{filename}"
    return f"{base}/{quote(path, safe='/')}"

def encontrar_mes_disponible_vert(anio: int, mes: int, max_retro: int = 12) -> tuple[int, int] | None:
    """¡Versión correcta!: usa GET normal (sin Range) para .xlsx."""
    for _ in range(max_retro):
        url = construye_vertimientos_url(anio, mes)
        if _exists_simple_get(url):
            return anio, mes
        anio, mes = ((anio - 1, 12) if mes == 1 else (anio, mes - 1))
    return None

# ======================================================
# CMG / CV / OP URLs (coordinador.cl wp-content)        
# ======================================================
def construye_cmg_real_url(d: date, base="https://www.coordinador.cl/wp-content/uploads") -> str:
    # OJO: esta es la URL "obvia". Para robustez real, usamos resolver_cmg_url_con_browser_por_dia().
    ymd_short = d.strftime("%y%m%d")
    url = f"{base}/{d:%Y/%m}/Antecedentes_CMG_Real_def_{ymd_short}.zip"
    return _normalize_coordinador_host(url)

def construye_costos_variables_url(d: date, base="https://www.coordinador.cl/wp-content/uploads") -> str:
    url = f"{base}/{d:%Y/%m}/COSTOSVARIABLES{d:%Y%m%d}.zip"
    return _normalize_coordinador_host(url)

def construye_politicas_operacion_url(d: date, base="https://www.coordinador.cl/wp-content/uploads") -> str:
    # Si es el día 1, calculamos el día anterior para obtener el año/mes del mes previo
    if d.day == 1:
        fecha_referencia = d - timedelta(days=1)
    else:
        fecha_referencia = d
    url = f"{base}/{fecha_referencia:%Y/%m}/PROGRAMA{d:%Y%m%d}.zip"
    return _normalize_coordinador_host(url)

def construye_politicas_operacion_url_variantes(
    d: date,
    base="https://www.coordinador.cl/wp-content/uploads",
    max_suffix: int = 3,
) -> list[str]:
    """
    Devuelve las variantes en orden: -max_suffix ... -1, y al final sin sufijo.
    """
    base_url = construye_politicas_operacion_url(d, base=base)
    variantes: list[str] = []
    for k in range(max_suffix, 0, -1):
        variantes.append(base_url.replace(".zip", f"-{k}.zip"))
    variantes.append(base_url)  # sin sufijo al final
    return variantes

# ======================================================
# Selenium: sesión reutilizable para todo un bloque
# ======================================================
class _BrowserSession:
    def __init__(self, download_dir: Path, headless: bool = False, debug: bool = True):
        self.download_dir = download_dir.resolve()
        self.headless = headless
        self.debug = debug
        self.driver = None

    def __enter__(self):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options as ChromeOptions

        self.download_dir.mkdir(parents=True, exist_ok=True)

        opts = ChromeOptions()
        opts.page_load_strategy = "eager"
        if self.headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--window-size=1366,768")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        # reduce casos raros de ERR_NAME_NOT_RESOLVED por DoH
        opts.add_argument("--disable-features=DnsOverHttps")

        if not self.headless:
            # visible por defecto; cerraremos en __exit__ salvo KEEP_CHROME_OPEN=1
            opts.add_experimental_option("detach", True)

        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        opts.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(options=opts)

        # “Sembrar” cookies con reintentos
        try:
            ok = self._safe_get("https://www.coordinador.cl/")
            import time
            time.sleep(1.0)
            if not ok:
                self._safe_get("https://coordinador.cl/")
                time.sleep(1.0)
        except Exception as e:
            log_warn(f"No se pudo abrir home coordinador.cl: {e}")

        return self

    def __exit__(self, exc_type, exc, tb):
        keep_open = os.environ.get("KEEP_CHROME_OPEN", "0") == "1"
        if self.driver and not keep_open:
            try:
                self.driver.quit()
                log_info("Ventana de Chrome cerrada correctamente.")
            except Exception as e:
                log_warn(f"No se pudo cerrar Chrome: {e}")

    def _safe_get(self, url: str, max_tries: int = 4) -> bool:
        """driver.get con reintentos y normalización de host."""
        import time
        from selenium.common.exceptions import WebDriverException

        url = _normalize_coordinador_host(url)

        def _backoff(i: int) -> float:
            return 0.5 * (i + 1)  # 0.5, 1.0, 1.5…

        for i in range(max_tries):
            try:
                self.driver.get(url)
                return True
            except WebDriverException as e:
                msg = str(e)
                wait = _backoff(i)
                if "ERR_NAME_NOT_RESOLVED" in msg or "net::ERR_NAME_NOT_RESOLVED" in msg:
                    log_warn(f"DNS no resolvió ({i+1}/{max_tries}). Reintento en {wait:.1f}s…")
                    time.sleep(wait)
                    continue
                log_warn(f"driver.get falló ({i+1}/{max_tries}): {e}. Reintento en {wait:.1f}s…")
                time.sleep(wait)
        return False

    def descargar(self, url: str) -> Path | None:
        """
        Descarga 1 URL usando la misma ventana.
        ✅ Robustez:
        - Espera el archivo EXACTO esperado por nombre.
        - Evita devolver "el zip más reciente" (que puede ser el de ayer).
        """
        from urllib.parse import urlparse as _uparse, unquote as _unq
        import time

        url = _normalize_coordinador_host(url)
        expected_name = _unq(url.split("/")[-1])  # ej: Antecedentes_CMG_Real_def_251031.zip
        expected_path = self.download_dir / expected_name

        # snapshot de estado antes
        before_files = {p.name for p in self.download_dir.glob("*")}
        t0 = time.time()

        # Ir a la carpeta del recurso (mejor referer)
        try:
            p = _uparse(url)
            dir_url = f"{p.scheme}://{p.netloc}/" + "/".join(p.path.split("/")[:-1]) + "/"
            ok = self._safe_get(dir_url)
            if not ok:
                log_warn(f"No se pudo abrir la carpeta {dir_url} (seguimos).")
            time.sleep(0.6)
        except Exception:
            pass

        # Abrir archivo con reintentos
        ok = self._safe_get(url)
        if not ok:
            log_warn(f"No se pudo abrir el archivo (GET) tras reintentos: {url}")
            return None

        # Esperar a que aparezca el archivo esperado y termine de descargarse
        timeout = 240
        while time.time() - t0 < timeout:
            time.sleep(0.5)

            # 1) si ya existe el archivo exacto, validamos que no esté en descarga
            if expected_path.exists():
                # En Chrome, mientras descarga, existe *.crdownload
                cr = expected_path.with_suffix(expected_path.suffix + ".crdownload")
                if not cr.exists():
                    return expected_path

            # 2) si apareció algún archivo nuevo, revisamos si coincide por nombre (casos raros de renombre)
            after_files = {p.name for p in self.download_dir.glob("*")}
            new_names = after_files - before_files

            # Si Chrome renombra (ej: "archivo (1).zip"), preferimos el exacto, pero aceptamos variante
            for nm in sorted(new_names):
                if nm.lower().endswith(".zip") or nm.lower().endswith(".xlsx"):
                    # Si es exactamente el nombre -> ok
                    if nm == expected_name:
                        pth = self.download_dir / nm
                        cr = pth.with_suffix(pth.suffix + ".crdownload")
                        if not cr.exists():
                            return pth

        # Timeout: si el archivo exacto no apareció, no inventamos
        return None
    
    def probe_status_head(self, url: str, timeout: int = 20) -> int | None:
        """
        Devuelve status HTTP usando fetch HEAD desde el browser (NO descarga archivos).
        - Retorna int (200, 404, 403, etc.) o None si falla.
        """
        import time
        from selenium.common.exceptions import WebDriverException

        url = _normalize_coordinador_host(url)

        try:
            self._safe_get("https://www.coordinador.cl/")
            time.sleep(0.5)
        except Exception:
            pass

        # timeout param se deja por compat; el JS tiene aborts internos
        script = r"""
            const url = arguments[0];
            const done = arguments[arguments.length - 1];

            (async () => {
            try {
                const ctrl = new AbortController();
                const t = setTimeout(() => ctrl.abort(), 15000);

                let r = await fetch(url, {
                    method: "HEAD",
                    cache: "no-store",
                    credentials: "include",
                    signal: ctrl.signal
                });

                clearTimeout(t);
                done(r.status);
            } catch (e) {
                try {
                    const ctrl2 = new AbortController();
                    const t2 = setTimeout(() => ctrl2.abort(), 5000);

                    let r2 = await fetch(url, {
                        method: "GET",
                        cache: "no-store",
                        credentials: "include",
                        signal: ctrl2.signal
                    });

                    clearTimeout(t2);
                    done(r2.status);
                } catch (e2) {
                    done(null);
                }
            }
            })();
        """

        try:
            st = self.driver.execute_async_script(script, url)
            return int(st) if st is not None else None
        except WebDriverException:
            return None
        except Exception:
            return None

# ======================================================
# Descarga con requests (unitaria) y en paralelo
# ======================================================
def _requests_download(url: str, carpeta: Path) -> Path | None:
    """Descarga un archivo con requests. Devuelve Path o None."""
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = unquote(url.split("/")[-1])
    ruta = carpeta / nombre
    if ruta.exists():
        log_warn(f"Ya existe, se omite: {ruta}")
        return ruta

    with requests.Session() as s:
        s.headers.update(BROWSER_HEADERS)
        candidates = _coordinador_variants(url) if "coordinador.cl" in url else [url]
        last_err: Exception | None = None
        for candidate in candidates:
            headers = {}
            if "coordinador.cl" in candidate:
                headers["Referer"] = _dir_referer(candidate)
                try:
                    s.get("https://www.coordinador.cl/", timeout=10, allow_redirects=True)
                except Exception:
                    pass
            elif not _probe_ok(candidate):
                log_warn(f"No se confirmó existencia (probe). Intentando GET: {candidate}")

            log_info(f"Descargando: {candidate}")
            try:
                with s.get(candidate, stream=True, timeout=180, allow_redirects=True, headers=headers) as r:
                    r.raise_for_status()
                    total = int(r.headers.get("Content-Length", 0))
                    descargado = 0
                    with open(ruta, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):
                            if not chunk:
                                continue
                            f.write(chunk)
                            descargado += len(chunk)
                            if total > 0:
                                pct = descargado * 100 // total
                                sys.stderr.write(
                                    f"\r   → {nombre} | {descargado/1e6:.2f} MB / {total/1e6:.2f} MB ({pct}%)"
                                )
                                sys.stderr.flush()
                sys.stderr.write("\n")
                log_info(f"Guardado en: {ruta}")
                return ruta
            except Exception as e:
                last_err = e
                log_warn(f"Intento fallido con {candidate}: {e}")
        if last_err:
            raise last_err

def descargar_plabacom(url: str, carpeta: Path = Path("data")) -> Path | None:
    """Compat: wrapper sobre _requests_download; si falla, marca en ARCHIVOS_NO_ENCONTRADOS."""
    try:
        return _requests_download(url, carpeta)
    except Exception as e:
        log_error(f"No se pudo descargar {url}: {e}")
        ARCHIVOS_NO_ENCONTRADOS.append(url)
        return None

def prioridad_descarga():
    try:
        if sys.platform.startswith("win"):
            import ctypes
            HIGH_PRIORITY_CLASS = 0x00000080
            ctypes.windll.kernel32.SetPriorityClass(
                ctypes.windll.kernel32.GetCurrentProcess(), HIGH_PRIORITY_CLASS
            )
        else:
            os.nice(-5)
    except Exception:
        pass

def descargar_en_paralelo(urls: list[str], max_workers: int = 3, carpeta: Path = Path("data")) -> list[Path]:
    rutas_ok: list[Path] = []
    if not urls:
        return rutas_ok
    log_info(f"Iniciando descargas en paralelo: {len(urls)} archivos, workers={max_workers}")
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut_por_url = {ex.submit(descargar_plabacom, url, carpeta): url for url in urls}
        for fut in as_completed(fut_por_url):
            url = fut_por_url[fut]
            try:
                ruta = fut.result()
                if ruta:
                    rutas_ok.append(ruta)
            except Exception as e:
                log_error(f"Fallo inesperado descargando {url}: {e}")
    log_info(f"Descargas finalizadas. OK={len(rutas_ok)} / TOTAL={len(urls)}")
    return rutas_ok

# ======================================================
# BLOQUE coordinador.cl con fallback de UNA ventana
# ======================================================
def _descargar_bloque_coordinador(
    urls: list[str],
    carpeta: Path,
    max_workers: int = 3,
    usar_headless: bool = False,
    debug: bool = True,
) -> list[Path]:
    """
    1) Mirar el PRIMER URL del bloque:
       - Si status 403 → usar Chrome (una sola ventana) para TODO el bloque.
       - Si 200/206 → intentar con requests (paralelo). Si alguno da 403, pasamos TODO a Chrome.
    """
    ok: list[Path] = []
    if not urls:
        return ok

    st = _first_status(urls[0])
    if st == 403:
        log_warn("403 en el primer recurso del bloque. Usando navegador para todo el bloque…")
        with _BrowserSession(carpeta, headless=usar_headless, debug=debug) as br:
            for u in urls:
                try:
                    destino = carpeta / unquote(u.split("/")[-1])
                    if destino.exists():
                        log_info(f"Ya existe, se omite (Chrome): {destino.name}")
                        ok.append(destino)
                        continue

                    p = br.descargar(u)
                    if p and p.exists():
                        ok.append(p)
                    else:
                        log_warn(f"No se obtuvo archivo para: {u}")
                except Exception as e:
                    log_warn(f"Falla descargando {u} con navegador: {e} (continuamos)")
                    continue
        return ok

    ok = descargar_en_paralelo(urls, max_workers=max_workers, carpeta=carpeta)

    fallidos = [u for u in urls if (carpeta / unquote(u.split("/")[-1])).exists() is False]
    if fallidos:
        alguno_403 = any((_first_status(u) == 403) for u in fallidos)
        if alguno_403:
            log_warn("Detectado 403 en elementos del bloque. Reintentando todo con navegador…")
            with _BrowserSession(carpeta, headless=usar_headless, debug=debug) as br:
                for u in urls:
                    try:
                        destino = carpeta / unquote(u.split("/")[-1])
                        if destino.exists():
                            continue
                        p = br.descargar(u)
                        if p and p.exists():
                            ok.append(p)
                        else:
                            log_warn(f"No se obtuvo archivo para: {u}")
                    except Exception as e:
                        log_warn(f"Falla descargando {u} con navegador: {e} (continuamos)")
                        continue

    return ok

# ======================================================
# Resolución de variantes PROGRAMA...-k.zip usando UNA sola ventana Chrome
# ======================================================
def resolver_politicas_operacion_url_con_browser(
    br: _BrowserSession,
    d: date,
    base="https://www.coordinador.cl/wp-content/uploads",
    max_suffix: int = 3,
) -> str:
    variantes = construye_politicas_operacion_url_variantes(d, base=base, max_suffix=max_suffix)

    for u in variantes:
        nombre = u.split("/")[-1]
        log_info(f"[resolve+chrome] {d} probando {nombre} (HEAD/fetch) ...")
        try:
            st = br.probe_status_head(u, timeout=20)
            if st is not None and 200 <= st < 400:
                log_info(f"[resolve+chrome] {d} ELEGIDA {nombre} (st={st})")
                return u
            log_info(f"[resolve+chrome] {d} descartada {nombre} (st={st})")
        except Exception as e:
            log_warn(f"[resolve+chrome] {d} fallo probando {nombre}: {e}")

    log_warn(f"[resolve+chrome] {d} ninguna variante dio 2xx/3xx; usando fallback sin sufijo")
    return variantes[-1]

# ======================================================
# Lotes
# ======================================================
def descargar_balance_energia_plabacom(anio: int, mes: int, carpeta: Path ):
    inicio_dt = datetime.now()
    log_info(f"Comienza descarga del balance de energía (solicitado {anio}-{mes:02d})")
    hallado = encontrar_mes_disponible_te(anio, mes)
    if not hallado:
        log_error("No se encontró ningún mes disponible para balance de energía.")
        return
    anio_ok, mes_ok = hallado
    if (anio_ok, mes_ok) != (anio, mes):
        log_warn(f"No hay datos para {anio}-{mes:02d}. Usando {anio_ok}-{mes_ok:02d}")

    cod_fecha = f"{str(anio_ok)[-2:]}{mes_ok:02d}"
    prioridad_descarga()
    urls = [
        construye_plabacom_url(nombre_archivo_transferencias_economicas(p, cod_fecha), anio_ok, mes_ok)
        for p in PREFIJOS_BALANCE
    ]
    descargar_en_paralelo(urls, max_workers=3, carpeta=carpeta)
    if ARCHIVOS_NO_ENCONTRADOS:
        log_warn(f"No descargados ({len(ARCHIVOS_NO_ENCONTRADOS)}):")
        for u in ARCHIVOS_NO_ENCONTRADOS:
            log_warn(f" - {u}")
    else:
        log_info(f"Balance de energía OK en {datetime.now() - inicio_dt}")

def descargar_balance_sscc_plabacom(anio: int, mes: int, carpeta: Path ):
    inicio_dt = datetime.now()
    log_info(f"Comienza descarga del balance de SSCC (solicitado {anio}-{mes:02d})")
    fecha = date(anio, mes, 1)
    nombre_archivo = nombre_archivo_sscc(PREFIJOS_SSCC, fecha)
    url = construye_plabacom_url_sscc(nombre_archivo, anio, mes)
    prioridad_descarga()
    descargar_plabacom(url, carpeta)
    if ARCHIVOS_NO_ENCONTRADOS:
        log_warn(f"No descargados ({len(ARCHIVOS_NO_ENCONTRADOS)}):")
        for u in ARCHIVOS_NO_ENCONTRADOS:
            log_warn(f" - {u}")
    else:
        log_info(f"Balance de SSCC OK en {datetime.now() - inicio_dt}")

def descargar_vertimientos(anio: int, mes: int, carpeta: Path = Path("data/vertimientos")):
    hallado = encontrar_mes_disponible_vert(anio, mes)
    if not hallado:
        log_error("No se encontró archivo de Vertimientos.")
        return
    anio_ok, mes_ok = hallado
    if (anio_ok, mes_ok) != (anio, mes):
        log_warn(f"No hay Vertimientos para {anio}-{mes:02d}. Usando {anio_ok}-{mes_ok:02d}")
    url = construye_vertimientos_url(anio_ok, mes_ok)
    log_info(f"Vertimientos URL: {url}")
    _descargar_bloque_coordinador([url], carpeta, max_workers=1, usar_headless=False, debug=True)

def descargar_cmg_rango(
    inicio: date,
    fin: date,
    carpeta: Path,
    max_workers: int = 4,
    max_shift: int = 2,
    usar_headless: bool = False,
    debug: bool = True,
):
    """
    ✅ CMG robusto:
    - Resuelve POR DÍA la carpeta YYYY/MM correcta (shift+0..max_shift).
      Ej: 2025-10-31 puede estar en /2025/11/...
    - Luego descarga el bloque (requests o Chrome según 403).
    - No cambia el path local: TODO queda en `carpeta`.
    """
    dias = [inicio + timedelta(days=i) for i in range((fin - inicio).days + 1)]
    urls: list[str] = []

    with _BrowserSession(carpeta, headless=usar_headless, debug=debug) as br:
        for d in dias:
            u = resolver_cmg_url_con_browser_por_dia(
                br,
                d,
                base="https://www.coordinador.cl/wp-content/uploads",
                max_shift=max_shift,
            )
            urls.append(u)

    _descargar_bloque_coordinador(
        urls,
        carpeta,
        max_workers=max_workers,
        usar_headless=usar_headless,
        debug=debug,
    )

def descargar_costos_variables_rango(inicio: date, fin: date, carpeta: Path = Path("data/costos"), max_workers: int = 4):
    urls = [construye_costos_variables_url(inicio + timedelta(days=i)) for i in range((fin - inicio).days + 1)]
    _descargar_bloque_coordinador(urls, carpeta, max_workers=max_workers, usar_headless=False, debug=True)

def descargar_politicas_operacion_rango(
    inicio: date,
    fin: date,
    carpeta: Path,
    max_workers: int = 4,
    max_suffix: int = 3,
    usar_headless: bool = False,
    debug: bool = True,
):
    """
    1) Resolver, por día, cuál variante (-3/-2/-1/base) existe usando UNA sola ventana Chrome (sin descargar).
    2) Descargar el bloque completo UNA sola vez con _descargar_bloque_coordinador().
    """
    dias = [inicio + timedelta(days=i) for i in range((fin - inicio).days + 1)]

    urls_resueltas: list[str] = []
    with _BrowserSession(carpeta, headless=usar_headless, debug=debug) as br:
        for d in dias:
            u = resolver_politicas_operacion_url_con_browser(
                br, d,
                base="https://www.coordinador.cl/wp-content/uploads",
                max_suffix=max_suffix,
            )
            urls_resueltas.append(u)

    _descargar_bloque_coordinador(
        urls_resueltas,
        carpeta,
        max_workers=max_workers,
        usar_headless=usar_headless,
        debug=debug,
    )

# ======================================================
# CLI
# ======================================================
def main():
    import argparse
    p = argparse.ArgumentParser(description="Descargador PLABACOM/Coordinador (KISS)")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_te = sub.add_parser("te", help="Balance de energía (mes)")
    p_te.add_argument("--anio", type=int, required=True)
    p_te.add_argument("--mes", type=int, required=True)
    p_te.add_argument("--carpeta", type=Path, default=Path("data/te"))

    p_vert = sub.add_parser("vert", help="Vertimientos (mes)")
    p_vert.add_argument("--anio", type=int, required=True)
    p_vert.add_argument("--mes", type=int, required=True)
    p_vert.add_argument("--carpeta", type=Path, default=Path("data/vertimientos"))

    p_cmg = sub.add_parser("cmg", help="CMG Real (rango de fechas)")
    p_cmg.add_argument("--inicio", type=str, required=True)
    p_cmg.add_argument("--fin", type=str, required=True)
    p_cmg.add_argument("--carpeta", type=Path, default=Path("data/cmg"))
    p_cmg.add_argument("--workers", type=int, default=4)
    p_cmg.add_argument("--max-shift", type=int, default=2)

    p_cv = sub.add_parser("cv", help="Costos Variables (rango de fechas)")
    p_cv.add_argument("--inicio", type=str, required=True)
    p_cv.add_argument("--fin", type=str, required=True)
    p_cv.add_argument("--carpeta", type=Path, default=Path("data/costos"))
    p_cv.add_argument("--workers", type=int, default=4)

    p_op = sub.add_parser("op", help="Políticas de Operación (rango de fechas, PROGRAMA...)")
    p_op.add_argument("--inicio", type=str, required=True)
    p_op.add_argument("--fin", type=str, required=True)
    p_op.add_argument("--carpeta", type=Path, required=True)
    p_op.add_argument("--workers", type=int, default=4)
    p_op.add_argument("--max-suffix", type=int, default=3)

    args = p.parse_args()

    if args.cmd == "te":
        descargar_balance_energia_plabacom(args.anio, args.mes, args.carpeta)
    elif args.cmd == "vert":
        descargar_vertimientos(args.anio, args.mes, args.carpeta)
    elif args.cmd == "cmg":
        ini = datetime.strptime(args.inicio.strip(), "%Y-%m-%d").date()
        fin = datetime.strptime(args.fin.strip(), "%Y-%m-%d").date()
        descargar_cmg_rango(ini, fin, args.carpeta, args.workers, max_shift=args.max_shift)
    elif args.cmd == "cv":
        ini = datetime.strptime(args.inicio.strip(), "%Y-%m-%d").date()
        fin = datetime.strptime(args.fin.strip(), "%Y-%m-%d").date()
        descargar_costos_variables_rango(ini, fin, args.carpeta, args.workers)
    elif args.cmd == "op":
        ini = datetime.strptime(args.inicio.strip(), "%Y-%m-%d").date()
        fin = datetime.strptime(args.fin.strip(), "%Y-%m-%d").date()
        descargar_politicas_operacion_rango(ini, fin, args.carpeta, args.workers, args.max_suffix)

if __name__ == "__main__":
    main()