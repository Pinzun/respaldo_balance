# Refactor: Modularización del pipeline de descarga

## Contexto del proyecto

Pipeline de descarga y carga de datos del sistema eléctrico chileno.

Ruta del proyecto: `respaldo_balance/actualiza_balance/`

---

## Estado ANTES del refactor

### Estructura existente

```
actualiza_balance/
├── main.py                          # orquestador principal (no modificado)
├── config.json                      # configuración (no modificado)
└── src/
    ├── download_data.py             # orquestador de descargas
    ├── carga_bd.py
    └── download/
        ├── __init__.py
        ├── scraper.py               # ← MONOLÍTICO: ~947 líneas con TODAS las funciones
        └── scraper/
            ├── __init__.py          # solo stubs (NotImplementedError)
            └── descarga_gx_real.py  # único scraper ya migrado al nuevo formato
```

### Problema

`src/download/scraper.py` era un archivo monolítico de ~947 líneas con:
- Funciones de descarga mezcladas (PLABACOM, coordinador.cl, Selenium)
- Helpers HTTP compartidos
- Clase `_BrowserSession` (Selenium)
- CLI con subcomandos

`src/download/scraper/__init__.py` tenía **stubs** que lanzaban `NotImplementedError`:

```python
# __init__.py ANTES
from .descarga_gx_real import descargar_gx_real

def descargar_balance_energia_plabacom(*args, **kwargs):
    raise NotImplementedError("Pendiente de migrar al nuevo formato")

def descargar_balance_sscc_plabacom(*args, **kwargs):
    raise NotImplementedError("Pendiente de migrar al nuevo formato")
```

`src/download_data.py` importaba esas funciones (que eran stubs) y llamaba a las dos de PLABACOM:

```python
# download_data.py ANTES
from .download.scraper import (
    descargar_balance_energia_plabacom,
    descargar_balance_sscc_plabacom
)
```

**Nota sobre la coexistencia `scraper.py` / `scraper/`:**  
Python da prioridad al paquete (directorio con `__init__.py`) sobre el módulo (`.py`) cuando tienen el mismo nombre. Por lo tanto, cualquier `from .download.scraper import ...` resolvía al paquete `scraper/`, no al archivo `scraper.py`. El archivo monolítico quedaba accesible solo desde el CLI de scraper.py.

---

## Patrón a seguir: `descarga_gx_real.py`

Cada scraper debe:
1. Ser un archivo independiente en `src/download/scraper/`
2. Exponer **una función pública** importable para el orquestador
3. Tener un entry point `if __name__ == "__main__"` con **argparse** para correrlo standalone

```bash
# Ejemplos de uso standalone
python -m actualiza_balance.src.download.scraper.descarga_gx_real --anio 2026 --mes 2
python -m actualiza_balance.src.download.scraper.descarga_balance_energia --anio 2026 --mes 2
python -m actualiza_balance.src.download.scraper.descarga_cmg --inicio 2026-01-01 --fin 2026-01-31 --carpeta data/cmg
```

---

## Cambios realizados

### 1. Nuevo: `src/download/scraper/_shared.py`

Módulo interno con todos los helpers compartidos extraídos de `scraper.py`:

| Componente | Descripción |
|---|---|
| `log_info`, `log_warn`, `log_error` | Logging con prefijos UTF-8 |
| `BROWSER_HEADERS` | Headers tipo navegador para requests |
| `MESES_ES`, `_carpeta_mes()` | Mapeo mes int → nombre/carpeta |
| `_normalize_coordinador_host()` | Fuerza `www.coordinador.cl` |
| `_coordinador_variants()` | Variantes de URL coordinador |
| `_dir_referer()` | Referer = carpeta del recurso |
| `_probe_ok()` | Prueba existencia con GET parcial (Range) |
| `_exists_simple_get()` | Prueba existencia con GET normal |
| `_first_status()` | Obtiene HTTP status para decidir estrategia |
| `_BrowserSession` | Clase Selenium reutilizable para un bloque de descargas |
| `_requests_download()` | Descarga unitaria con requests + reintentos |
| `descargar_plabacom()` | Wrapper de `_requests_download` con manejo de errores |
| `prioridad_descarga()` | Sube prioridad del proceso (win/unix) |
| `descargar_en_paralelo()` | ThreadPoolExecutor sobre `descargar_plabacom` |
| `_descargar_bloque_coordinador()` | Descarga bloque: intenta requests, fallback a Chrome si 403 |
| `ARCHIVOS_NO_ENCONTRADOS` | Lista global de URLs fallidas |

---

### 2. Nuevo: `src/download/scraper/descarga_balance_energia.py`

**Función pública:** `descargar_balance_energia_plabacom(anio: int, mes: int, carpeta: Path)`

**Lógica:**
1. Busca hacia atrás hasta 12 meses el primer mes disponible en S3 (`encontrar_mes_disponible_te`)
2. Construye 3 URLs PLABACOM (prefijos: `01 Resultados`, `02 Antecedentes de Cálculo`, `03 Bases de Datos`)
3. Descarga en paralelo (3 workers)

**Helpers propios:**
- `PREFIJOS_BALANCE`
- `nombre_archivo_transferencias_economicas(prefijo, fecha, codigo, ext)`
- `construye_plabacom_url(nombre_archivo, anio, mes, ...)`
- `encontrar_mes_disponible_te(anio, mes, max_retro=12)`

**Argparse standalone:**
```bash
python -m actualiza_balance.src.download.scraper.descarga_balance_energia \
    --anio 2026 --mes 2 --carpeta data/energia
```

---

### 3. Nuevo: `src/download/scraper/descarga_balance_sscc.py`

**Función pública:** `descargar_balance_sscc_plabacom(anio: int, mes: int, carpeta: Path)`

**Lógica:**
1. Construye nombre de archivo con formato `Balance_SSCC_{anio}_{mes_abreviado}_def.zip`
2. Construye URL PLABACOM categoría SSCC
3. Descarga secuencial via `descargar_plabacom`

**Helpers propios:**
- `PREFIJOS_SSCC`
- `nombre_archivo_sscc(prefijo, fecha, codigo, ext)`
- `construye_plabacom_url_sscc(nombre_archivo, anio, mes, ...)`

**Argparse standalone:**
```bash
python -m actualiza_balance.src.download.scraper.descarga_balance_sscc \
    --anio 2026 --mes 2 --carpeta data/sscc
```

---

### 4. Nuevo: `src/download/scraper/descarga_cmg.py`

**Función pública:** `descargar_cmg_rango(inicio, fin, carpeta, max_workers=4, max_shift=2, ...)`

**Lógica (robusta):**
1. Para cada día del rango, resuelve la carpeta YYYY/MM correcta probando `shift+0..max_shift` meses hacia adelante (el archivo del día 31-oct puede estar en carpeta `/2025/11/`)
2. Usa UNA sola ventana Chrome para probar URLs (HEAD/fetch vía JS, sin descargar)
3. Descarga el bloque completo via `_descargar_bloque_coordinador`

**Helpers propios:**
- `_add_months(d, delta)` — suma meses sin pasar el último día del mes
- `_cmg_url_for_shift(d, month_shift, base)` — construye URL con carpeta desplazada
- `resolver_cmg_url_con_browser_por_dia(br, d, base, max_shift)` — resuelve URL correcta por día

**Argparse standalone:**
```bash
python -m actualiza_balance.src.download.scraper.descarga_cmg \
    --inicio 2026-01-01 --fin 2026-01-31 --carpeta data/cmg_real --workers 4 --max-shift 2
```

---

### 5. Nuevo: `src/download/scraper/descarga_politicas_operacion.py`

**Función pública:** `descargar_politicas_operacion_rango(inicio, fin, carpeta, max_workers=4, max_suffix=3, ...)`

**Lógica:**
1. Para cada día, prueba variantes de nombre: `PROGRAMA{yyyymmdd}-3.zip`, ..., `-1.zip`, `PROGRAMA{yyyymmdd}.zip`
2. Usa UNA sola ventana Chrome para detectar qué variante existe (HEAD/fetch)
3. Descarga el bloque completo via `_descargar_bloque_coordinador`

**Helpers propios:**
- `construye_politicas_operacion_url(d, base)` — URL base (si día 1, usa fecha del mes anterior)
- `construye_politicas_operacion_url_variantes(d, base, max_suffix)` — lista de variantes `-k..base`
- `resolver_politicas_operacion_url_con_browser(br, d, base, max_suffix)` — elige variante existente

**Argparse standalone:**
```bash
python -m actualiza_balance.src.download.scraper.descarga_politicas_operacion \
    --inicio 2026-01-01 --fin 2026-01-31 --carpeta data/operacion --workers 4 --max-suffix 3
```

---

### 6. Modificado: `src/download/scraper/__init__.py`

**Antes:** stubs con `NotImplementedError` para balance_energia y balance_sscc.

**Después:** exports reales de los 5 scrapers:

```python
from .descarga_gx_real import descargar_gx_real
from .descarga_balance_energia import descargar_balance_energia_plabacom
from .descarga_balance_sscc import descargar_balance_sscc_plabacom
from .descarga_cmg import descargar_cmg_rango
from .descarga_politicas_operacion import descargar_politicas_operacion_rango
```

---

### 7. Modificado: `src/download_data.py`

**Antes:** importaba solo 2 funciones (las otras eran stubs).

**Después:** importa las 4 funciones de descarga:

```python
from .download.scraper import (
    descargar_balance_energia_plabacom,
    descargar_balance_sscc_plabacom,
    descargar_cmg_rango,
    descargar_politicas_operacion_rango,
)
```

---

## Estructura DESPUÉS del refactor

```
actualiza_balance/
└── src/
    ├── download_data.py             # orquestador (imports actualizados)
    └── download/
        ├── __init__.py
        ├── scraper.py               # monolítico original (intacto, shadowed por el paquete)
        └── scraper/
            ├── __init__.py          # ← exports reales de los 5 scrapers
            ├── _shared.py           # ← NUEVO: helpers compartidos
            ├── descarga_gx_real.py  # sin cambios
            ├── descarga_balance_energia.py   # ← NUEVO
            ├── descarga_balance_sscc.py      # ← NUEVO
            ├── descarga_cmg.py               # ← NUEVO
            └── descarga_politicas_operacion.py  # ← NUEVO
```

---

## Decisiones de diseño

### ¿Por qué `_shared.py` en vez de copiar helpers en cada archivo?

`_BrowserSession` y `_descargar_bloque_coordinador` son ~200 líneas de lógica compleja (Selenium, manejo de 403, reintentos). Duplicar ese código en 4 archivos crearía deuda técnica inmediata. `_shared.py` es un módulo interno (prefijo `_`) que no forma parte de la API pública del paquete.

### ¿Por qué no modificar `scraper.py` monolítico?

Sigue siendo funcional como CLI (`python -m actualiza_balance.src.download.scraper ...`) y como referencia. Queda intacto; no es importado por ningún módulo nuevo (Python lo sombrea con el paquete `scraper/`).

### `ARCHIVOS_NO_ENCONTRADOS` es una lista por módulo

Cada archivo de scraper importa `ARCHIVOS_NO_ENCONTRADOS` de `_shared.py`. En la práctica, como cada scraper corre en un proceso separado (standalone) o en secuencia (orquestador), esto es correcto. Si en el futuro se corren en paralelo dentro del mismo proceso, se puede convertir en un manager de estado compartido.

---

## Pendiente / próximos pasos sugeridos

1. **Integrar CMG y Políticas en `ejecutar_descarga()`** — `download_data.py` ya importa `descargar_cmg_rango` y `descargar_politicas_operacion_rango` pero no las llama. Falta agregarlas al flujo de `ejecutar_descarga()` con las rutas correspondientes.

2. **Deprecar o eliminar `scraper.py` monolítico** — Una vez que todos los scrapers estén migrados y verificados en producción, el archivo monolítico puede eliminarse. El CLI equivalente queda en cada módulo standalone.

3. **Verificar en producción** — Correr con `download: true` en `config.json` para un mes reciente.
