# Contexto de Base de Datos — Modelo DDS

> Documento generado a partir del ANEXO 1 oficial del proyecto.  
> Contiene la clasificación de tablas, relaciones y diccionario de datos de la base de datos `balance`.  
> **⚠️ ADVERTENCIA:** La base de datos `importar_balance` está **en construcción** y puede sufrir cambios significativos en cualquier momento. Su estructura **no debe tratarse como verdad absoluta** ni usarse como referencia definitiva para desarrollo o análisis.

---

## 1. Clasificación de tablas según modelo DDS

| Nombre tabla | Clasificación |
|---|---|
| barra | dimensiones |
| central | dimensiones |
| cmg | hechos |
| codigoterritorio | dimensiones |
| contratos_financieros | hechos |
| contratos_fisicos | hechos |
| cv | hechos |
| empresa | dimensiones |
| gx_real | hechos |
| hora_mensual | dimensiones |
| inyecciones | hechos |
| medidores | dimensiones |
| pe_compensacion | hechos |
| pe_inyecciones | hechos |
| retiro | hechos |
| retiro_regulado | hechos |
| sobrecostos | hechos |
| sscc_infra | hechos |
| sscc_rt | hechos |
| subestacion | dimensiones |
| transmision | dimensiones |
| unidad_generacion | dimensiones |
| version | dimensiones |
| vertimiento | hechos |

---

## 2. Relaciones entre tablas

| Tabla | Primary Key (PK) | Tipo PK | Foreign Key (FK) | Tabla referenciada |
|---|---|---|---|---|
| barra | id_barra | surrogate | id_subestacion | subestacion |
| central | id_central | surrogate | — | — |
| cmg | (IdVersion, hora_Mensual, id_barra) | surrogate | id_hora / id_barra | hora_mensual / barra |
| codigo_territorio | idcomuna | natural | — | — |
| contratos_financieros | id_transaccion | surrogate | id_hora | hora_mensual |
| contratos_fisicos | id_transaccion | surrogate | rut_empresa / id_hora | empresa / hora_mensual |
| cv | (idVersion, hora_mensual, idUnidadgen) | surrogate | IdUnidadgen / id_hora | unidad_generacion / hora_mensual |
| empresa | rut_empresa | natural | — | — |
| gx_real | id_generacion | surrogate | id_central / id_hora | central / hora_mensual |
| hora_mensual | id_hora | surrogate | id_version | version |
| inyecciones | (id_version, clave, cuarto_hora) | surrogate | rut_empresa / id_hora / id_pe_inyeccion | empresa / hora_mensual / pe_inyecciones |
| medidores | id_medidor | surrogate | — | — |
| pe_compensacion | (idVersion, hora_mensual, idEmpresa) | surrogate | IdEmpresa / idVersion | empresa / version |
| pe_inyecciones | id_pe_inyeccion | surrogate | — | — |
| retiro | (idVersion, clave, cuarto_hora) | surrogate | — | — |
| retiro_regulado | (idversion, idempresa_br, idempresa_sum) | natural | idempresa_br / idempresa_sum / idversion | empresa / version |
| sobrecostos | (idVersion, hora_mensual, idUnidadgen) | surrogate | id_hora / idUnidadgen | hora_mensual / unidad_generacion |
| sscc_infra | (idVersion, idEmpresa) | surrogate | IdEmpresa / idVersion | empresa / version |
| sscc_rt | (idVersion, concepto, idEmpresa) | surrogate | IdEmpresa / idVersion | empresa / version |
| subestacion | id_subestacion | surrogate | idcomuna | codigoterritorio |
| transmision | (id_version, clave, cuarto_hora) | surrogate | id_hora / id_medidor | hora_mensual / medidores |
| unidad_generacion | id_unidad_generacion | surrogate | id_central | central |
| version | id_version | surrogate | — | — |
| vertimiento | id_vertimiento | surrogate | id_central / id_hora | central / hora_mensual |

---

## 3. Diccionario de datos — Base de datos: `balance`

### Tabla: `barra`

| Columna | Tipo | Descripción |
|---|---|---|
| nombre | VARCHAR(255) | Nombre de la barra en el sistema eléctrico nacional |
| tension | FLOAT | Nivel de tensión asociado a la barra |
| nombre_cmg | VARCHAR(255) | Nombre de la barra utilizada para cálculos de costo marginal |
| subestacion | TEXT | Nombre de la subestación a la que pertenece la barra |
| id_infotecnica | INT(11) | Identificador de la subestación entregado por la infotécnica |
| calificacion | TEXT | Zona dentro del sistema de transmisión donde se encuentra la S/E |
| id_empresa | INT(11) | Identificador surrogate de la empresa propietaria de la barra |
| id_barra | INT(11) | PK surrogate de la barra |
| vigente | TINYINT(1) | Indica si la barra sigue vigente en el sistema (booleano) |
| observacion | TEXT | Observaciones adicionales sobre la barra |
| barra_troncal | TINYINT(1) | Indica si la barra es troncal (booleano) |
| id_subestacion | INT(11) | FK surrogate hacia la subestación |

---

### Tabla: `central`

| Columna | Tipo | Descripción |
|---|---|---|
| id_central | INT(11) | PK surrogate de la central eléctrica |
| nombre_central | VARCHAR(255) | Nombre de la central en el SEN |
| id_infotecnica | INT(11) | Identificador único asignado por infotécnica |
| coordinado | VARCHAR(255) | Empresa encargada de la central |
| tipo | VARCHAR(80) | Clasificación tipo de central de generación |
| subtipo | VARCHAR(80) | Clasificación subtipo de central de generación |
| punto_conexion_sen | VARCHAR(255) | Punto de conexión al SI a través del cual inyecta energía |
| punto_conexion_sen_limpio | VARCHAR(255) | Nombre limpio del punto de conexión para interconexiones |
| id_subestacion | INT(11) | FK surrogate hacia la subestación conectada |
| tecnologia | VARCHAR(120) | Tipo de tecnología de la central |
| id_empresa | INT(11) | FK surrogate hacia la empresa propietaria |
| observacion | TEXT | Observaciones adicionales sobre la central |

---

### Tabla: `cmg`

| Columna | Tipo | Descripción |
|---|---|---|
| id_cmg | BIGINT(20) | PK surrogate del registro CMG |
| id_version | INT(11) | FK hacia la versión de la base de datos |
| id_hora | BIGINT(20) | FK hacia la hora de la medición |
| id_barra | INT(11) | FK hacia la barra |
| CMG_PESO_KWH | FLOAT | Costo marginal en CLP/kWh |
| CMG_DOLAR_MWH | FLOAT | Costo marginal en USD/MWh |
| dolar | FLOAT | Valor del dólar-peso en el periodo |

---

### Tabla: `codigo_territorio`

| Columna | Tipo | Descripción |
|---|---|---|
| id_region | INT(11) | Identificador surrogate de la región |
| nombre_region | VARCHAR(255) | Nombre de la región |
| abreviatura_region | VARCHAR(255) | Abreviatura de la región |
| id_provincia | INT(11) | Identificador surrogate de la provincia |
| nombre_provincia | VARCHAR(255) | Nombre de la provincia |
| id_comuna | INT(11) | PK natural — identificador único de la comuna |

---

### Tabla: `contratos_financieros`

| Columna | Tipo | Descripción |
|---|---|---|
| id_transaccion | BIGINT(20) | PK surrogate de la transacción financiera |
| id_version | INT(11) | FK hacia la versión de la base de datos |
| clave | VARCHAR(255) | Código representativo de la transacción, empresa y periodo |
| energia_kwh | FLOAT | Energía transada en el contrato [kWh] |
| cmg_clp_kwh | FLOAT | Costo marginal en CLP/kWh |
| valorizado_clp | FLOAT | Monto valorizado del contrato en CLP |
| rut_empresa | VARCHAR(255) | RUT de la empresa |
| id_barra | INT(11) | FK surrogate hacia la barra |
| transaccion | TEXT | Tipo de transacción (COMPRA / VENTA) |
| observacion | TEXT | Observaciones adicionales |
| id_contrato | INT(11) | Identificador surrogate del contrato |
| id_hora | BIGINT(20) | FK hacia la hora de la transacción |

---

### Tabla: `contratos_fisicos`

| Columna | Tipo | Descripción |
|---|---|---|
| id_version | INT(11) | FK hacia la versión de la base de datos |
| id_contrato | INT(11) | Identificador surrogate del contrato |
| observacion | TEXT | Observaciones adicionales |
| clave | VARCHAR(255) | Código representativo de la transacción y empresa |
| rut_empresa | VARCHAR(50) | RUT de la empresa |
| id_empresa | — | FK surrogate hacia la empresa |
| id_barra | INT(11) | FK surrogate hacia la barra |
| transaccion | TEXT | Tipo de transacción (COMPRA / VENTA) |
| id_hora | BIGINT(20) | FK surrogate hacia la hora de la transacción |
| cmg_clp_kwh | FLOAT | Costo marginal en CLP/kWh |
| energia_kwh | FLOAT | Energía transada en el contrato [kWh] |
| valorizado_clp | FLOAT | Monto valorizado del contrato en CLP |
| id_transaccion | BIGINT(20) | PK surrogate de la transacción |

---

### Tabla: `cv`

| Columna | Tipo | Descripción |
|---|---|---|
| id_version | INT(11) | FK hacia la versión de la base de datos |
| hora_mensual | — | Hora del mes en la cual se realiza la medición |
| id_hora | BIGINT(20) | FK surrogate hacia la hora |
| id_unidadgen | INT(11) | FK surrogate hacia la unidad generadora |
| cv_usd_mwh | FLOAT | Costo variable de la unidad en USD/MWh |

---

### Tabla: `gx_real`

| Columna | Tipo | Descripción |
|---|---|---|
| id_generacion | BIGINT(20) | PK surrogate del registro de generación |
| id_central | INT(11) | FK hacia la central eléctrica |
| nombre_unidadgen | VARCHAR(255) | Nombre de la unidad generadora |
| id_version | INT(11) | FK hacia la versión de la base de datos |
| inyeccion_retiro | DECIMAL(18,6) | Energía inyectada o retirada desde la central [kWh] |
| id_hora | BIGINT(20) | FK surrogate hacia el periodo horario |
| subtipo | VARCHAR(255) | Subtipo de la generación |

---

### Tabla: `hora_mensual`

| Columna | Tipo | Descripción |
|---|---|---|
| id_hora | BIGINT(20) | PK surrogate — cuenta los periodos dentro del mes |
| id_version | INT(11) | FK hacia la versión de la base de datos |
| cuarto_hora | INT(11) | Identificador de cuartos de hora dentro del mes |
| dia | INT(11) | Día del mes |
| hora | INT(11) | Hora del día |
| minuto | INT(11) | Minuto (intervalos de 15 minutos) |
| fecha_hora | DATETIME | Fecha y hora del registro de balance |
| trimestre | TINYINT(4) | Trimestre del año |
| dow | TINYINT(4) | Día de la semana |
| año | SMALLINT(6) | Año al que corresponde el registro |
| mes | TINYINT(4) | Mes al que corresponde el registro |

---

### Tabla: `inyecciones`

| Columna | Tipo | Descripción |
|---|---|---|
| id_version | INT(11) | FK hacia la versión de la base de datos |
| clave | VARCHAR(255) | Código representativo de la barra donde se realizan las inyecciones |
| cuarto_hora | INT(11) | Identificador de cuartos de hora dentro del mes |
| med_hor_2 | DECIMAL(25,5) | Energía final mensual ajustada tras el proceso de balance energético zonal [kWh] |
| med_hor | DECIMAL(25,5) | Energía medida mensual directamente por el medidor [kWh] |
| cmg_peso_kwh | DECIMAL(20,5) | Costo marginal en CLP/kWh |
| valorizado_pesos | DECIMAL(20,5) | Monto valorizado en CLP |
| rut_empresa | VARCHAR(13) | RUT de la empresa |
| id_hora | BIGINT(20) | FK surrogate hacia la hora |
| id_pe_inyeccion | INT(11) | FK surrogate hacia la inyección |
| id_medidor | INT(11) | FK surrogate hacia el medidor |

---

### Tabla: `medidores`

| Columna | Tipo | Descripción |
|---|---|---|
| id_medidor | INT(11) | PK surrogate del medidor |
| clave | VARCHAR(255) | Código representativo de la barra, nivel de tensión, paño y empresa |
| id_barra | INT(11) | FK surrogate hacia la barra |
| nro_lt | DECIMAL(18,5) | Número de la línea de transmisión donde está el medidor |
| clave_lt | VARCHAR(255) | Clave de la línea de transmisión |
| id_empresa | VARCHAR(13) | FK surrogate hacia la empresa |
| tipo1 | VARCHAR(50) | Clasificación del origen de la energía del medidor |
| zona | VARCHAR(100) | Zona del país donde se encuentra el medidor |

---

### Tabla: `pe_compensacion`

| Columna | Tipo | Descripción |
|---|---|---|
| id_version | INT(11) | FK hacia la versión de la base de datos |
| hora_mensual | INT(11) | Hora del mes en la cual se realiza la medición |
| id_empresa | VARCHAR(13) | FK surrogate hacia la empresa |
| prorrata_suministrador | DECIMAL(40,20) | Factor de prorrateo aplicado al suministrador |
| diferencia_horaria | DECIMAL(40,20) | Diferencia entre el precio nudo a corto plazo y el CMG dentro del periodo |
| compensacion | DECIMAL(40,20) | Monto asociado a la compensación resultante del proceso de balance |

---

### Tabla: `pe_inyecciones`

| Columna | Tipo | Descripción |
|---|---|---|
| id_version | INT(11) | FK hacia la versión de la base de datos |
| clave | VARCHAR(255) | Código representativo del tipo y nombre de la central |
| cuarto_hora | INT(11) | Identificador de cuartos de hora dentro del mes |
| precio_nudo | DECIMAL(40,20) | Precio de nudo aplicado en el punto de inyección |
| valorizado_pnudo | DECIMAL(40,20) | Monto valorizado según precio nudo y energía inyectada |
| diferencia_pnudo_cmg | DECIMAL(40,20) | Diferencia entre valorización a precio nudo y CMG |
| energia_sobre_9mwh | DECIMAL(40,20) | Energía inyectada que excede los 9 MWh |
| medida_15min_ajustada | DECIMAL(40,20) | Diferencia entre la medida horaria y la energía sobre 9 MW |
| observacion | TEXT | Observaciones adicionales |
| id_pe_inyeccion | INT(11) | PK surrogate del registro de inyección |

---

### Tabla: `retiro`

| Columna | Tipo | Descripción |
|---|---|---|
| id_version | INT(11) | FK hacia la versión de la base de datos |
| clave | VARCHAR(255) | Código representativo del medidor, barra, nivel de tensión, paño y empresa |
| cuarto_hora | INT(11) | Identificador de cuartos de hora dentro del mes |
| med_hor_2 | DECIMAL(25,5) | Energía final mensual ajustada tras el proceso de balance energético zonal [kWh] |
| med_hor | DECIMAL(25,5) | Energía medida mensual directamente por el medidor [kWh] |
| cmg_peso_kwh | DECIMAL(20,5) | Costo marginal en clp/kWh |
| valorizado_pesos | DECIMAL(20,5) | Monto valorizado por el retiro de energía [CLP] |
| id_medidor | INT(11) | FK surrogate hacia el medidor |
| id_hora | BIGINT(20) | FK surrogate hacia la hora |

---

### Tabla: `retiro_regulado`

| Columna | Tipo | Descripción |
|---|---|---|
| id_retiro_regulado | INT(11) | PK surrogate del retiro regulado |
| id_version | INT(11) | FK hacia la versión de la base de datos |
| bloque_regulado | VARCHAR(10) | Bloque horario regulado |
| idempresa_br | INT(11) | FK hacia la empresa distribuidora |
| idempresa_sum | INT(11) | FK hacia la empresa suministradora |
| kwh_ps1 | FLOAT | Asignación de energía para suministradoras dentro del bloque horario |
| %_ps1 | FLOAT | Porcentaje de energía correspondiente a la suministradora respecto al total |
| kwh_ps2 | FLOAT | Asignación de energía para suministradoras (PS2) |
| %_ps2 | FLOAT | Porcentaje PS2 respecto al total |
| fisico_kwh | FLOAT | Energía física retirada en el bloque horario |
| monetario | FLOAT | Monto asociado al retiro de energía |

---

### Tabla: `sobrecostos`

| Columna | Tipo | Descripción |
|---|---|---|
| id_version | INT(11) | FK hacia la versión de la base de datos |
| hora_mensual | INT(11) | Hora del mes en la cual se realiza la medición |
| id_hora | BIGINT(20) | FK surrogate hacia la hora de la medición |
| id_unidadgen | INT(11) | FK surrogate hacia la unidad generadora |
| tipo | TEXT | Tipo de servicio que está prestando la unidad generadora |
| sobrecosto_clp | FLOAT | Monto correspondiente al sobrecosto [CLP] |
| zona_pago | TEXT | Zona en la que se encuentra la empresa que recibirá el retiro |
| gen | FLOAT | Generación utilizada para proveer el servicio complementario |
| cons_propio | FLOAT | Consumo propio de la unidad generadora en el periodo |
| cv | FLOAT | Costo variable del periodo y zona de la unidad generadora |
| cmg | FLOAT | Costo marginal del periodo y zona de la unidad generadora |
| sscc | TEXT | Tipo de servicios complementarios que presenta la unidad |

---

### Tabla: `sscc_infra`

> Servicios complementarios de infraestructura — requieren instalaciones físicas adicionales e involucran inversiones en activos de red.

| Columna | Tipo | Descripción |
|---|---|---|
| id_version | INT(11) | FK hacia la versión de la base de datos |
| id_empresa | VARCHAR(13) | FK surrogate hacia la empresa |
| remuneracion | FLOAT | Monto de remuneración otorgado a la empresa por SSCC |
| recaudacion | FLOAT | Monto de recaudación solicitado a la empresa por SSCC |
| neto | FLOAT | Diferencia entre montos remunerados y recaudados |

---

### Tabla: `sscc_rt`

> Servicios complementarios por recurso técnico — prestaciones que dependen de las capacidades operativas del sistema y se proveen directamente desde las centrales.

| Columna | Tipo | Descripción |
|---|---|---|
| id_version | INT(11) | FK hacia la versión de la base de datos |
| concepto | TEXT | Clasificación de SSCC que el usuario provee al sistema eléctrico |
| id_empresa | VARCHAR(13) | FK surrogate hacia la empresa |
| recibe | FLOAT | Monto que recibirá la empresa |
| paga | FLOAT | Monto que pagará la empresa |
| sen | FLOAT | Diferencia entre montos recibidos y pagados |

---

### Tabla: `subestacion`

| Columna | Tipo | Descripción |
|---|---|---|
| id_subestacion | INT(11) | PK surrogate de la subestación |
| nombre | VARCHAR(50) | Nombre de la subestación |
| id_region | INT(11) | FK surrogate hacia la región |
| id_provincia | INT(11) | FK surrogate hacia la provincia |
| id_comuna | INT(11) | FK hacia la comuna (codigoterritorio) |
| tipo_configuracion | VARCHAR(50) | Tipo de configuración de la subestación |
| entrada_en_operacion | VARCHAR(50) | Fecha de entrada en operación |
| coordenada_este | VARCHAR(20) | Posición horizontal en metros (sistema UTM) |
| coordenada_norte | VARCHAR(20) | Posición vertical en metros (sistema UTM) |
| huso | VARCHAR(10) | Huso horario de la subestación |
| observacion | VARCHAR(30) | Observaciones adicionales |

---

### Tabla: `transmision`

| Columna | Tipo | Descripción |
|---|---|---|
| id_version | INT(11) | FK hacia la versión de la base de datos |
| clave | VARCHAR(255) | Código representativo de la barra, nivel de tensión, paño y empresa |
| cuarto_hora | INT(11) | Identificador de cuartos de hora dentro del mes |
| med_hor_2 | DECIMAL(25,5) | Energía final mensual ajustada tras el proceso de balance energético zonal [kWh] |
| med_hor | DECIMAL(25,5) | Energía medida directamente por el medidor [kWh] |
| cmg_peso_kwh | DECIMAL(20,5) | Costo marginal en CLP/kWh |
| valorizado_pesos | DECIMAL(20,5) | Monto valorizado en CLP |
| id_hora | BIGINT(20) | FK surrogate hacia la hora de la medición |
| id_medidor | INT(11) | FK surrogate hacia el medidor |

---

### Tabla: `unidad_generacion`

| Columna | Tipo | Descripción |
|---|---|---|
| id_unidad_generacion | INT(11) | PK surrogate de la unidad de generación |
| nombre | VARCHAR(255) | Nombre de la unidad de generación |
| id_central | INT(11) | FK surrogate hacia la central |
| combustible | VARCHAR(255) | Tipo de combustible utilizado por la unidad |

---

### Tabla: `version`

| Columna | Tipo | Descripción |
|---|---|---|
| id_version | INT(11) | PK surrogate de la versión |
| periodo | DATE | Periodo al que corresponde la base de datos |
| tipo | VARCHAR(255) | Clasificación del estado de la base de datos |
| nombre | VARCHAR(255) | Nombre del archivo que contiene la base de datos |
| año | INT(11) | Año del periodo |
| mes | INT(11) | Mes del periodo |

---

### Tabla: `vertimiento`

| Columna | Tipo | Descripción |
|---|---|---|
| id_vertimiento | BIGINT(20) | PK surrogate del vertimiento |
| id_version | BIGINT(20) | FK hacia la versión de la base de datos |
| id_central | INT(11) | FK hacia la central |
| id_unidadgen | INT(11) | FK surrogate hacia la unidad generadora |
| nombre_unidadgen | VARCHAR(255) | Nombre de la unidad generadora |
| id_hora | BIGINT(20) | FK surrogate hacia la hora de la medición |
| vertimiento | FLOAT | Cantidad de energía vertida en el periodo [kWh] |
| tipo | TEXT | Clasificación de la tecnología de la unidad que vertió energía |

---

## 4. Base de datos: `importar_balance` ⚠️ EN CONSTRUCCIÓN

> **⚠️ IMPORTANTE:** Esta base de datos está **en construcción activa**. Su estructura, nombres de columnas y tipos de datos pueden cambiar drásticamente en cualquier momento. No debe utilizarse como referencia definitiva para desarrollo ni análisis. La información aquí descrita es meramente orientativa.

### Tabla: `balance`

| Columna | Tipo |
|---|---|
| nombre_barra | VARCHAR(100) |
| tension | INT |
| clave | VARCHAR(255) |
| nro_lt | VARCHAR(50) |
| cuarto_hora | INT |
| fecha_medicion | DATETIME |
| razon_social | VARCHAR(255) |
| rut | VARCHAR(20) |
| nombre_corto | VARCHAR(100) |
| descripcion | VARCHAR(255) |
| id_contrato | VARCHAR(255) |
| tipo | VARCHAR(50) |
| precio | VARCHAR(50) |
| zona | VARCHAR(100) |
| medida_1 | DECIMAL(25,5) |
| medida_2 | DECIMAL(25,5) |
| medida_2a | DECIMAL(25,5) |
| medida_3 | DECIMAL(25,5) |
| cmg[clp/KWh] | DECIMAL(20,5) |
| valorizado_clp | DECIMAL(20,5) |

### Tabla: `barras`

| Columna | Tipo |
|---|---|
| barra | VARCHAR(50) |
| nivel_tension | INT |
| id_infotecnica | INT |
| id_cne | VARCHAR(50) |
| nombre_cne | VARCHAR(50) |
| subestacion | VARCHAR(100) |
| comuna | VARCHAR(50) |
| calificacion | VARCHAR(100) |
| zona_concesion | VARCHAR(50) |
| empresa_propietaria | VARCHAR(255) |
| zona_transmision | VARCHAR(100) |

### Tabla: `cmg`

| Columna | Tipo |
|---|---|
| nombre_barra | VARCHAR(50) |
| tension | INT |
| fecha | DATE |
| hora | TINYINT |
| minuto | TINYINT |
| cmg[clp/kwh] | DECIMAL(10,5) |
| cmg[usd/kwh] | DECIMAL(10,5) |
| intervalo | INT |
| cuarto_hora | TINYINT |
| nombre_barra_cmg | VARCHAR(50) |
| usd | DECIMAL(10,2) |

### Tabla: `contratos`

| Columna | Tipo |
|---|---|
| nombre_barra | VARCHAR(255) |
| tension | VARCHAR(50) |
| clave | VARCHAR(255) |
| nro_lt | VARCHAR(50) |
| cuarto_hora | INT |
| fecha_medicion | DATETIME |
| razon_social | VARCHAR(255) |
| rut | VARCHAR(50) |
| nombre_corto | VARCHAR(255) |
| descripcion | VARCHAR(255) |
| id_contrato | INT |
| tipo | VARCHAR(50) |
| precio | DECIMAL(40,20) |
| zona | VARCHAR(50) |
| medida_1 | DECIMAL(40,20) |
| medida_2 | DECIMAL(40,20) |
| medida_3 | DECIMAL(40,20) |
| cmg_clp_kwh | DECIMAL(40,20) |
| valorizado_clp | DECIMAL(40,20) |

### Tabla: `retiro_regulado`

| Columna | Tipo |
|---|---|
| bloque_regulado | VARCHAR(100) |
| suministrador | VARCHAR(100) |
| kwh_ps1 | FLOAT |
| porcentaje_ps1 | FLOAT |
| kwh_ps2 | FLOAT |
| fisico_kwh | FLOAT |
| monetario | FLOAT |

### Tabla: `compensacion`

| Columna | Tipo |
|---|---|
| cuarto_hora | INT |
| suministrador | VARCHAR(100) |
| prorrata_suministro | DECIMAL(40,20) |
| diferencia_horaria | DECIMAL(40,20) |
| compensacion | DECIMAL(40,20) |

### Tabla: `inyecciones`

| Columna | Tipo |
|---|---|
| cuarto_hora | INT |
| clave | VARCHAR(255) |
| razon_social | VARCHAR(255) |
| rut | VARCHAR(20) |
| nombre_corto | VARCHAR(255) |
| descripcion | VARCHAR(255) |
| nombre_barra_cmg | VARCHAR(255) |
| tipo | VARCHAR(10) |
| precio_pncp | DECIMAL(40,20) |
| medida_1 | DECIMAL(40,20) |
| cmg_peso_kwh | DECIMAL(40,20) |
| valorizado_cmg | DECIMAL(40,20) |
| valorizado_pncp | DECIMAL(40,20) |
| diferencia_pncp_cmg | DECIMAL(40,20) |

### Tabla: `sobrecostos`

| Columna | Tipo |
|---|---|
| cuarto_hora | DATE |
| hora | INT |
| tipo | VARCHAR(50) |
| central | VARCHAR(255) |
| sobrecosto_clp | FLOAT |
| zona_pago | VARCHAR(50) |
| gen | FLOAT |
| cons_propio | FLOAT |
| cv | FLOAT |
| cmg | FLOAT |
| sscc | TEXT |

### Tabla: `sscc_rt`

| Columna | Tipo |
|---|---|
| concepto | VARCHAR(255) |
| empresa | VARCHAR(255) |
| recibe | FLOAT |
| paga | FLOAT |
| sen | FLOAT |

### Tabla: `vertimiento`

> ⚠️ Nota: en `importar_balance` esta tabla corresponde a SSCC infraestructura (remuneración/recaudación), no a vertimiento de energía renovable como en `balance`.

| Columna | Tipo |
|---|---|
| empresa | VARCHAR(255) |
| remuneracion | FLOAT |
| recaudacion | FLOAT |
| neto | FLOAT |
