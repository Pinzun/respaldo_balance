"""
_shared.py — Helpers compartidos entre los scrapers del coordinador/PLABACOM.
"""
from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

import requests

# ======================================================
# UTF-8 seguro
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
# Headers tipo navegador + utilidades HTTP
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
        opts.add_argument("--disable-features=DnsOverHttps")

        if not self.headless:
            opts.add_experimental_option("detach", True)

        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        opts.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(options=opts)

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
            return 0.5 * (i + 1)

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
        """Descarga 1 URL usando la misma ventana."""
        from urllib.parse import urlparse as _uparse, unquote as _unq
        import time

        url = _normalize_coordinador_host(url)
        expected_name = _unq(url.split("/")[-1])
        expected_path = self.download_dir / expected_name

        before_files = {p.name for p in self.download_dir.glob("*")}
        t0 = time.time()

        try:
            p = _uparse(url)
            dir_url = f"{p.scheme}://{p.netloc}/" + "/".join(p.path.split("/")[:-1]) + "/"
            ok = self._safe_get(dir_url)
            if not ok:
                log_warn(f"No se pudo abrir la carpeta {dir_url} (seguimos).")
            time.sleep(0.6)
        except Exception:
            pass

        ok = self._safe_get(url)
        if not ok:
            log_warn(f"No se pudo abrir el archivo (GET) tras reintentos: {url}")
            return None

        timeout = 240
        while time.time() - t0 < timeout:
            time.sleep(0.5)

            if expected_path.exists():
                cr = expected_path.with_suffix(expected_path.suffix + ".crdownload")
                if not cr.exists():
                    return expected_path

            after_files = {p.name for p in self.download_dir.glob("*")}
            new_names = after_files - before_files

            for nm in sorted(new_names):
                if nm.lower().endswith(".zip") or nm.lower().endswith(".xlsx"):
                    if nm == expected_name:
                        pth = self.download_dir / nm
                        cr = pth.with_suffix(pth.suffix + ".crdownload")
                        if not cr.exists():
                            return pth

        return None

    def probe_status_head(self, url: str, timeout: int = 20) -> int | None:
        """Devuelve status HTTP usando fetch HEAD desde el browser."""
        import time
        from selenium.common.exceptions import WebDriverException

        url = _normalize_coordinador_host(url)

        try:
            self._safe_get("https://www.coordinador.cl/")
            time.sleep(0.5)
        except Exception:
            pass

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
    """Wrapper sobre _requests_download; si falla, marca en ARCHIVOS_NO_ENCONTRADOS."""
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
