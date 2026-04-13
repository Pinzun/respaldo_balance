# respaldo_balance

Pipeline ETL para la carga mensual del balance de energía del mercado eléctrico chileno. Descarga archivos desde el portal PLABACOM del Coordinador Eléctrico Nacional, los procesa y los carga en una base de datos relacional.

Soporta dos motores de base de datos seleccionables en `config.json`:
- **MySQL / MariaDB** — implementación original
- **PostgreSQL** — implementación paralela en migración activa

---

## Estructura del proyecto

```
respaldo_balance/
└── actualiza_balance/
    ├── main.py                  # Punto de entrada
    ├── config.json              # Parámetros de ejecución
    ├── requirements.txt
    ├── .env                     # Variables de entorno (no versionado)
    └── src/
        ├── download_data.py     # Orquestador de descarga
        ├── carga_bd.py          # Orquestador de carga a BD
        ├── download/
        │   └── scraper/         # Scrapers por tipo de archivo
        │       ├── descarga_balance_energia.py
        │       ├── descarga_balance_sscc.py
        │       └── descarga_gx_real.py
        ├── core/
        │   ├── <modulo>.py      # Lógica MySQL para cada módulo
        │   └── <modulo>_pg.py   # Equivalente PostgreSQL
        └── db/
            ├── db_utils.py      # Conexión MySQL (SSH / directa)
            ├── db_utils_pg.py   # Conexión PostgreSQL (SSH / directa)
            ├── router.py        # Selección de motor unificada
            ├── crea_importar.sql    # Schema staging MySQL
            └── crea_importar_pg.sql # Schema staging PostgreSQL
```

### Módulos de carga (`src/core/`)

| Módulo | Contenido |
|---|---|
| `cmg` | Costos marginales por barra |
| `barras` | Información de barras eléctricas |
| `balance` | Medidas de generación, retiro y transmisión |
| `contratos` | Contratos financieros y físicos |
| `factor_retiro_regulado` | Factor de retiro regulado |
| `precio_estabilizado` | Compensaciones e inyecciones |
| `sobrecostos` | Sobrecostos de operación |
| `sscc` | Servicios complementarios |
| `vertimiento` | Vertimiento de centrales |

Cada módulo expone: `preflight_*`, `procesar_*`, `importar_*`, `revisar_*`, `cargar_*`.

---

## Bases de datos

### MySQL / MariaDB

| BD | Rol |
|---|---|
| `balance` | Tablas definitivas |
| `importar_balance` | Tablas staging |

### PostgreSQL

Una sola BD con dos schemas:

| Schema | Rol |
|---|---|
| `mercado_corto_plazo` | Tablas definitivas |
| `importar_mcp` | Tablas staging |

---

## Configuración

### 1. Variables de entorno (`.env`)

Copia `.env.example` a `.env` y completa los valores:

```
# MySQL / MariaDB
DB_SSH_HOST=
DB_SSH_PORT=22
DB_SSH_USER=
DB_SSH_PASSWORD=
DB_HOST_REMOTE=127.0.0.1
DB_PORT_REMOTE=3306
DB_USER=
DB_PASSWORD=
DB_NAME=balance

# PostgreSQL
PG_SSH_HOST=
PG_SSH_PORT=22
PG_SSH_USER=
PG_SSH_PASSWORD=
PG_HOST=127.0.0.1
PG_PORT=5432
PG_USER=
PG_PASSWORD=
PG_DB=mercado_corto_plazo
```

### 2. `config.json`

```json
{
  "fecha_inicio": "2025-10-01",
  "fecha_fin":    "2025-10-31",
  "workers":      4,
  "server_mode":  "direct",
  "dry_run":      true,
  "part1_exec":   false,
  "part2_exec":   true,
  "tipo":         "Definitivo",
  "download":     false,
  "carga":        true,
  "db_engine":    "mysql"
}
```

| Parámetro | Valores | Descripción |
|---|---|---|
| `server_mode` | `"direct"` / `"ssh"` | Conexión directa o a través de túnel SSH |
| `dry_run` | `true` / `false` | Si es `true`, ejecuta ROLLBACK al final (no persiste cambios) |
| `part1_exec` | `true` / `false` | Ejecuta carga a tablas staging |
| `part2_exec` | `true` / `false` | Ejecuta carga a tablas definitivas |
| `tipo` | `"Definitivo"` / `"Preliminar"` | Tipo de período |
| `download` | `true` / `false` | Descarga archivos desde PLABACOM |
| `carga` | `true` / `false` | Ejecuta la carga a BD |
| `db_engine` | `"mysql"` / `"postgresql"` | Motor de base de datos |

---

## Instalación

```bash
pip install -r actualiza_balance/requirements.txt
```

Para PostgreSQL se requiere además que `libpq` esté disponible en el sistema (`psycopg2-binary` lo incluye en la mayoría de plataformas).

---

## Ejecución

Desde la raíz del repositorio:

```bash
python -m actualiza_balance.main 
```

El script lee `config.json`, descarga los archivos si `download: true` y carga la BD si `carga: true`.

### Flujo de carga

```
preflight  →  PART1 (staging)  →  PART2 (definitivo)
```

1. **Preflight** — verifica que los archivos de insumo estén presentes y con formato correcto.
2. **Part 1** — procesa los archivos CSV y los carga en las tablas staging (`importar_balance` / `importar_mcp`).
3. **Part 2** — valida los datos en staging y los mueve a las tablas definitivas (`balance` / `mercado_corto_plazo`).

Ambas partes pueden ejecutarse de forma independiente mediante `part1_exec` y `part2_exec`.

### Inicializar la base de datos (PostgreSQL)

Crea la base de datos `mercado_corto_plazo` y toda su estructura (tablas, índices y vistas).
Debe ejecutarse **una sola vez** antes de la primera carga, con el usuario de PostgreSQL configurado en `.env`.

```bash
python -m actualiza_balance.src.db.estructura_mercado_corto_plazo_pg
```

También acepta modo SSH:

```python
from actualiza_balance.src.db.estructura_mercado_corto_plazo_pg import crear_estructura_mercado_corto_plazo

crear_estructura_mercado_corto_plazo(server_mode="ssh")
```

### Inicializar el schema staging (PostgreSQL)

```bash
python -m actualiza_balance.src.db.crea_importar_pg
```

---

## Dependencias principales

| Librería | Uso |
|---|---|
| `pandas` | Procesamiento de CSVs |
| `pymysql` | Conexión MySQL / MariaDB |
| `psycopg2-binary` | Conexión PostgreSQL |
| `paramiko` | Túnel SSH (MySQL) |
| `sshtunnel` | Túnel SSH (PostgreSQL) |
| `selenium` | Scraping de PLABACOM |
| `openpyxl` | Lectura de archivos Excel |
