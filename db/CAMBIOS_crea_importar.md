# Cambios en `crea_importar.sql`

**Fecha:** 2026-04-09  
**Autor:** revisión Claude (claude-sonnet-4-6)  
**Criterio:** las columnas de cada tabla se derivan de lo que las funciones `cargar_*` y `revisar_*` usan realmente en sus queries SQL, **no** de los `CREATE TABLE IF NOT EXISTS` que los scripts Python generan en tiempo de ejecución (que contienen errores respecto a las queries de carga final).

---

## Resumen de lo que se hizo

1. Se completó el script con la creación de **13 tablas** (9 de datos + 4 de mapeo).
2. Se corrigieron inconsistencias entre los CREATE TABLE embebidos en Python y los SELECT/JOIN de las funciones `cargar_*`.
3. Se eliminaron los `DROP DATABASE IF EXISTS importar` e `importar_` para limpiar bases legadas.
4. Se agregaron comentarios que indican módulo origen, CSV de entrada y tabla destino en producción.

---

## Tablas creadas

| Tabla | Tipo | Módulo origen | Tabla destino en `balance` |
|---|---|---|---|
| `cmg` | datos | `cmg.py` | `balance.cmg` |
| `barras_importadas` | datos | `barras.py` | `balance.barra_info` |
| `balance` | datos | `balance.py` | `balance.generacion`, `retiro`, `transmision`, `relacion`, `empresa` |
| `contratos` | datos | `contratos.py` | `balance.c_fin_info`, `c_fin_med`, `c_fis_info`, `c_fis_med` |
| `retiroregulado` | datos | `factor_retiro_regulado.py` | `balance.retiro_regulado` |
| `compensacion` | datos | `precio_estabilizado.py` | `balance.pe_compensacion` |
| `inyecciones` | datos | `precio_estabilizado.py` | `balance.pe_inyecciones` |
| `cv_importado` | datos | `sobrecostos.py` | `balance.cv` |
| `sobrecostos` | datos | `sobrecostos.py` | `balance.sobrecostos` |
| `sscc_rt` | datos | `sscc.py` | `balance.sscc_rt` |
| `sscc_infra` | datos | `sscc.py` | `balance.sscc_infra` |
| `vertimiento` | datos | `vertimiento.py` | `balance.vertimiento` |
| `empresa2` | mapeo | manual | (lookup para `balance.empresa`) |
| `barra2` | mapeo | manual | (lookup para `balance.barra`) |
| `descripcion2` | mapeo | manual | (lookup para `balance.descripcion`) |
| `unidadgen2` | mapeo | manual | (lookup para `balance.unidadgeneracion`) |

---

## Inconsistencias encontradas en los scripts Python

Estas diferencias deben corregirse en los scripts Python para que el LOAD DATA INFILE use los nombres de columna correctos.

### 1. `cmg.py` — `cargar_cmg` usa columnas de `barra2` sobre `barras_importadas`

**Problema:**  
`cargar_cmg` hace JOIN con `importar.barras_importadas` usando `bi.col_1` y `bi.nombrebarra`, que son las columnas de la tabla de mapeo `barra2`, no de `barras_importadas`.

```sql
-- Actual (incorrecto):
LEFT JOIN importar.barras_importadas bi ON bi.col_1 = t.nombre_barra_cmg
LEFT JOIN balance.barra b ON b.nombre = bi.nombrebarra;

-- Debería ser:
LEFT JOIN importar_balance.barra2 b2 ON b2.col_1 = t.nombre_barra_cmg
LEFT JOIN balance.barra b ON b.nombre = b2.nombrebarra;
```

**Impacto:** `cargar_cmg` no resuelve correctamente el `idBarra`, dejando NULLs en `balance.cmg`.

---

### 2. `cmg.py` — `revisar_cmg` usa columnas raw del CSV sobre `barras_importadas`

**Problema:**  
`revisar_cmg` hace JOIN con `importar.barras_importadas` usando `bi.Barra` y `bi.Nombre barra CNE` (nombres del Excel original), que no coinciden con la tabla `barras_importadas` tal como debe quedar definida.

```sql
-- Actual (inconsistente con cargar_barras_info):
LEFT JOIN importar.barras_importadas bi ON bi.Barra = t.nombre_barra_cmg
LEFT JOIN balance.barra b ON b.nombre = bi.`Nombre barra CNE`

-- Debería ser (usando barra2 como lookup, igual que cargar_cmg):
LEFT JOIN importar_balance.barra2 b2 ON b2.col_1 = t.nombre_barra_cmg
LEFT JOIN balance.barra b ON b.nombre = b2.nombrebarra
```

---

### 3. `balance.py` — columnas `CMg[CLP/KWh]` y `valorizado_CLP` en CREATE TABLE no coinciden con cargar

**Problema:**  
El `CREATE TABLE` del script define `CMg[CLP/KWh]` y `valorizado_CLP`, pero `cargar_balance` referencia `t.cmg_pesos_kwh` y `t.valorizado_pesos`.

**Corrección aplicada en SQL:**  
La tabla `balance` en `importar_balance` usa `cmg_pesos_kwh` y `valorizado_pesos`.  
**Pendiente:** actualizar el LOAD DATA INFILE en `balance.py` para que use esos nombres de columna.

---

### 4. `contratos.py` — columnas `cmg_clp_kwh` y `valorizado_clp` no coinciden con cargar

**Problema:**  
El `CREATE TABLE` del script define `cmg_clp_kwh` y `valorizado_clp`, pero `cargar_contratos` referencia `c.cmg_peso_kwh` y `c.valorizado_pesos`.

**Corrección aplicada en SQL:**  
La tabla `contratos` usa `cmg_peso_kwh` y `valorizado_pesos`.  
**Pendiente:** actualizar el LOAD DATA INFILE en `contratos.py`.

---

### 5. `factor_retiro_regulado.py` — nombre de tabla `retiro_regulado` vs `retiroregulado`

**Problema:**  
El `CREATE TABLE` del script crea la tabla como `importar.retiro_regulado`, pero todas las queries de `revisar_frr` y `cargar_frr` referencian `importar.retiroregulado` (sin guión bajo entre "retiro" y "regulado").

**Corrección aplicada en SQL:**  
La tabla se llama `retiroregulado` (sin guión bajo).  
**Pendiente:** corregir el `CREATE TABLE` en `factor_retiro_regulado.py` para que coincida.

---

### 6. `factor_retiro_regulado.py` — columnas `porcentaje_ps1/2` vs `%_ps1/2`

**Problema:**  
El `CREATE TABLE` del script define `porcentaje_ps1` y `porcentaje_ps2`, pero `cargar_frr` referencia `` r.`%_ps1` `` y `` r.`%_ps2` ``.

**Corrección aplicada en SQL:**  
Las columnas se llaman `` `%_ps1` `` y `` `%_ps2` `` (con backticks por el carácter especial).  
**Pendiente:** corregir el LOAD DATA INFILE en `factor_retiro_regulado.py`.

---

### 7. `precio_estabilizado.py` — `cuarto_hora` vs `hora_mensual` en compensacion

**Problema:**  
El `CREATE TABLE` del script define la columna como `cuarto_hora`, pero `cargar_compensacion` referencia `t.hora_mensual`.

**Corrección aplicada en SQL:**  
La tabla `compensacion` usa `hora_mensual`.  
**Pendiente:** verificar qué valor trae realmente el CSV y si corresponde a `cuarto_hora` o `hora_mensual`.

---

### 8. `sobrecostos.py` — `central` vs `unidadgen` en cv_importado y sobrecostos

**Problema:**  
Los `CREATE TABLE` de ambas tablas definen la columna como `central`, pero `cargar_sobrecostos` referencia `t.unidadgen` en el JOIN con `unidadgen2`.

**Corrección aplicada en SQL:**  
Ambas tablas usan `unidadgen`.  
**Pendiente:** actualizar LOAD DATA INFILE en `sobrecostos.py`.

---

### 9. `vertimiento.py` — referencia a base de datos `importar_` (legacy)

**Problema:**  
`vertimiento.py` referencia `importar_.vertimiento` e `importar_.unidadgen2` (con guión bajo al final), una base de datos antigua que ya no existe.

**Corrección aplicada en SQL:**  
La tabla `vertimiento` se crea en `importar_balance`.  
**Pendiente:** actualizar `vertimiento.py` para usar `importar_balance.vertimiento` e `importar_balance.unidadgen2`.

---

## Notas adicionales

- **`gx_real.py`** no tiene staging en esta BD: exporta directamente a CSVs sin pasar por `importar_balance`. Se excluye de este script.
- Las tablas de mapeo (`empresa2`, `barra2`, `descripcion2`, `unidadgen2`) se crean **vacías**. Su contenido debe cargarse manualmente o con un script separado antes de ejecutar PART2.
- El nombre de la BD staging es `importar_balance`. Todos los scripts Python que actualmente usan `importar.` o `importar_.` deben actualizarse para usar `importar_balance.`.
