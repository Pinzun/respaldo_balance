-- =============================================================================
-- crea_importar.sql
-- Crea la base de datos staging importar_balance y todas sus tablas.
--
-- CRITERIO DE DISEÑO: las columnas de cada tabla se derivan de los campos
-- que las funciones cargar_* y revisar_* consumen efectivamente, NO de los
-- CREATE TABLE que los scripts Python generan en tiempo de ejecución
-- (que contienen inconsistencias respecto a las queries de carga final).
--
-- Las tablas de mapeo (empresa2, barra2, descripcion2, unidadgen2) son
-- lookup manuales; se crean vacías y se poblan fuera de este script.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Creación de la BD staging
-- -----------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS importar_balance
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_general_ci;

USE importar_balance;


-- =============================================================================
-- TABLAS DE DATOS (cargadas desde CSV por los scripts Python)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- cmg
-- Módulo   : src/core/cmg.py → procesar_cmg / importar_cmg
-- CSV      : data/processed/cmg/{YYYY}/{YYMM}/cmg{YYMM}_15min_formateado.csv
-- Destino  : balance.cmg  (vía cargar_cmg)
--
-- Columnas inferidas de cargar_cmg (join con balance.cmg) y cargar_barras_info
-- (subquery que lee nombre_barra + tension + nombre_barra_cmg de esta tabla).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_balance.cmg (
    nombre_barra        VARCHAR(50),
    tension             INT,
    nombre_barra_cmg    VARCHAR(50),
    cuarto_hora         INT,           -- llamado "Cuarto de Hora" en el CSV original
    cmg_peso_kwh        DECIMAL(10,5), -- "CMg[CLP/KWh]"
    cmg_dolar_mwh       DECIMAL(10,5), -- "CMg[USD/MWh]"
    dolar               DECIMAL(10,2)  -- "USD"
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- -----------------------------------------------------------------------------
-- barras_importadas
-- Módulo   : src/core/barras.py → procesar_barras / importar_barras
-- CSV      : data/processed/energia/{YYYY}/{YYMM}/{YYMM}_Barras.csv
-- Destino  : balance.barra_info  (vía cargar_barras_info)
--
-- Columnas inferidas de cargar_barras_info (SELECT t.nombre_barra, t.tension,
-- t.subestacion, t.barra_infotecnica, t.codigo_cne, t.nombre_barra_cne,
-- t.comuna, t.calificacion, t.zona_concesion, t.zona_transicion) y de
-- revisar_barras_info (SELECT DISTINCT empresa FROM importar.barras_importadas).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_balance.barras_importadas (
    nombre_barra        VARCHAR(50),
    tension             INT,
    barra_infotecnica   INT,
    codigo_cne          VARCHAR(50),
    nombre_barra_cne    VARCHAR(100),
    subestacion         VARCHAR(100),
    comuna              VARCHAR(50),
    calificacion        VARCHAR(100),
    zona_concesion      VARCHAR(50),
    zona_transicion     VARCHAR(100),
    empresa             VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- -----------------------------------------------------------------------------
-- balance
-- Módulo   : src/core/balance.py → procesar_medidas / importar_balance
-- CSVs     : {YYMM}_{D/P}_VALORIZADO_NORTE/SUR/NORTE_Dx/SUR_Dx.csv
-- Destino  : balance.empresa, balance.relacion, balance.generacion,
--            balance.retiro, balance.transmision  (vía cargar_balance)
--
-- Columnas inferidas de cargar_balance:
--   INSERT INTO balance.generacion/retiro/transmision usa
--   clave, cuarto_hora, medida_2, medida_1, cmg_pesos_kwh, valorizado_pesos.
--   INSERT INTO balance.relacion usa
--   clave, nro_lt, rut, descripcion, id_contrato, zona, precio, tipo,
--   nombre_barra, tension.
--   INSERT INTO balance.empresa usa rut, nombre_corto.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_balance.balance (
    nombre_barra        VARCHAR(100),
    tension             INT,
    clave               VARCHAR(255),
    nro_lt              VARCHAR(50),
    cuarto_hora         INT,
    fecha_medicion      DATETIME,
    rut                 VARCHAR(20),
    nombre_corto        VARCHAR(100),
    descripcion         VARCHAR(255),
    id_contrato         VARCHAR(50),
    tipo                VARCHAR(50),
    precio              VARCHAR(50),
    zona                VARCHAR(100),
    medida_1            DECIMAL(25,5),
    medida_2            DECIMAL(25,5),
    cmg_pesos_kwh       DECIMAL(20,5),
    valorizado_pesos    DECIMAL(20,5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- -----------------------------------------------------------------------------
-- contratos
-- Módulo   : src/core/contratos.py → importar_contratos
-- CSV      : data/processed/balance/{YYMM}_{D/P}_contratos.csv
-- Destino  : balance.c_fin_info, balance.c_fin_med,
--            balance.c_fis_info, balance.c_fis_med  (vía cargar_contratos)
--
-- Columnas inferidas de cargar_contratos:
--   INSERT INTO c_fin_info / c_fis_info: id_contrato, descripcion, clave,
--     rut, nombre_barra, tension, tipo (='C_FIN'|'C_FIS').
--   INSERT INTO c_fin_med / c_fis_med: clave, cuarto_hora, medida_1,
--     cmg_peso_kwh, valorizado_pesos.
--   INSERT INTO balance.empresa: rut, nombre_corto.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_balance.contratos (
    nombre_barra        VARCHAR(255),
    tension             INT,
    clave               VARCHAR(255)  NOT NULL,
    rut                 VARCHAR(20),
    nombre_corto        VARCHAR(255),
    descripcion         VARCHAR(255),
    id_contrato         INT,
    tipo                VARCHAR(50),   -- 'C_FIN' o 'C_FIS'
    cuarto_hora         INT,
    medida_1            DECIMAL(40,20),
    cmg_peso_kwh        DECIMAL(40,20),
    valorizado_pesos    DECIMAL(40,20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- -----------------------------------------------------------------------------
-- retiroregulado
-- Módulo   : src/core/factor_retiro_regulado.py → procesar_frr / importar_frr
-- CSV      : data/processed/frr/retiroregulado_{YYMM}.csv
-- Destino  : balance.retiro_regulado  (vía cargar_frr)
--
-- Columnas inferidas de cargar_frr:
--   INSERT INTO balance.retiro_regulado usa
--   bloque_regulado (→ empresa via empresa2), suministrador (→ empresa),
--   kwh_ps1, %_ps1, kwh_ps2, %_ps2, fisico_kwh, monetario.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_balance.retiroregulado (
    bloque_regulado     VARCHAR(100),
    suministrador       VARCHAR(100),
    kwh_ps1             FLOAT,
    `%_ps1`             FLOAT,
    kwh_ps2             FLOAT,
    `%_ps2`             FLOAT,
    fisico_kwh          FLOAT,
    monetario           FLOAT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- -----------------------------------------------------------------------------
-- compensacion
-- Módulo   : src/core/precio_estabilizado.py → procesar_compensacion / importar_pe
-- CSV      : data/processed/precio_estabilizado/{YYMM}_compensacion.csv
-- Destino  : balance.pe_compensacion  (vía cargar_compensacion)
--
-- Columnas inferidas de cargar_compensacion:
--   INSERT INTO balance.pe_compensacion usa
--   hora_mensual (INT, no cuarto_hora), suministrador (→ empresa via empresa2),
--   prorrata_suministrador, diferencia_horaria, compensacion.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_balance.compensacion (
    hora_mensual            INT,
    suministrador           VARCHAR(100),
    prorrata_suministrador  DECIMAL(40,20),
    diferencia_horaria      DECIMAL(40,20),
    compensacion            DECIMAL(40,20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- -----------------------------------------------------------------------------
-- inyecciones
-- Módulo   : src/core/precio_estabilizado.py → procesar_inyecciones / importar_pe
-- CSVs     : {YYMM}_inyecciones_norte.csv, {YYMM}_inyecciones_sur.csv
-- Destino  : balance.pe_inyecciones  (vía cargar_inyecciones)
--            + validaciones cruzadas con balance.generacion y balance.relacion
--
-- Columnas inferidas de cargar_inyecciones y revisar_inyecciones:
--   clave, cuarto_hora, precio_pncp, valorizado_pncp, diferencia_pncp_cmg,
--   rut, nombre_corto, descripcion, nombre_barra_cmg, tipo,
--   medida_1 (generación), CMG_PESO_KWH.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_balance.inyecciones (
    cuarto_hora             INT,
    clave                   VARCHAR(255),
    rut                     VARCHAR(20),
    nombre_corto            VARCHAR(255),
    descripcion             VARCHAR(255),
    nombre_barra_cmg        VARCHAR(255),
    tipo                    VARCHAR(10),
    precio_pncp             DECIMAL(40,20),
    medida_1                DECIMAL(40,20),
    cmg_peso_kwh            DECIMAL(40,20),
    valorizado_cmg          DECIMAL(40,20),
    valorizado_pncp         DECIMAL(40,20),
    diferencia_pncp_cmg     DECIMAL(40,20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- -----------------------------------------------------------------------------
-- cv_importado
-- Módulo   : src/core/sobrecostos.py → importar_sobrecostos
-- CSV      : data/processed/sobrecostos/{YYMM}_costosvariables.csv
-- Destino  : balance.cv  (vía cargar_sobrecostos)
--
-- Columnas inferidas de cargar_sobrecostos (carga a balance.cv):
--   fecha, hora → join con balance.hora_mensual (DAY(fecha) y hora)
--   unidadgen   → join con unidadgen2 (NOT 'central' como figura en el CREATE TABLE del script)
--   cv_usd_mwh  → valor insertado
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_balance.cv_importado (
    fecha           DATE          NOT NULL,
    hora            INT           NOT NULL,
    unidadgen       VARCHAR(255)  NOT NULL,
    cv_usd_mwh      FLOAT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- -----------------------------------------------------------------------------
-- sobrecostos
-- Módulo   : src/core/sobrecostos.py → importar_sobrecostos
-- CSV      : data/processed/sobrecostos/{YYMM}_sobrecostos.csv
-- Destino  : balance.sobrecostos  (vía cargar_sobrecostos)
--
-- Columnas inferidas de cargar_sobrecostos (carga a balance.sobrecostos):
--   fecha, hora → join con hora_mensual
--   unidadgen   → join con unidadgen2 (NOT 'central')
--   tipo, sobrecosto_clp, zona_pago, gen, cons_propio, cv, cmg, sscc → insertados
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_balance.sobrecostos (
    fecha           DATE          NOT NULL,
    hora            INT           NOT NULL,
    tipo            VARCHAR(50),
    unidadgen       VARCHAR(255)  NOT NULL,
    sobrecosto_clp  FLOAT,
    zona_pago       VARCHAR(50),
    gen             FLOAT,
    cons_propio     FLOAT,
    cv              FLOAT,
    cmg             FLOAT,
    sscc            TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- -----------------------------------------------------------------------------
-- sscc_rt
-- Módulo   : src/core/sscc.py → importar_sscc
-- CSV      : data/processed/sscc/sscc_rt_{YYMM}.csv
-- Destino  : balance.sscc_rt  (vía cargar_sscc)
--
-- Columnas inferidas de cargar_sscc y revisar_sscc.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_balance.sscc_rt (
    concepto    VARCHAR(255),
    empresa     VARCHAR(255),
    recibe      FLOAT,
    paga        FLOAT,
    sen         FLOAT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- -----------------------------------------------------------------------------
-- sscc_infra
-- Módulo   : src/core/sscc.py → importar_sscc
-- CSV      : data/processed/sscc/sscc_infra_{YYMM}.csv
-- Destino  : balance.sscc_infra  (vía cargar_sscc)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_balance.sscc_infra (
    empresa         VARCHAR(255),
    remuneracion    FLOAT,
    recaudacion     FLOAT,
    neto            FLOAT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- -----------------------------------------------------------------------------
-- vertimiento
-- Módulo   : src/core/vertimiento.py → importar_vertimiento
-- CSV      : data/processed/reducciones/Vertimiento_{YYMM}.csv
-- Destino  : balance.vertimiento  (vía cargar_vertimientos)
--
-- Columnas inferidas de cargar_vertimientos:
--   central → join con unidadgen2; fecha, hora → join con hora_mensual;
--   kwh, tipo → insertados.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_balance.vertimiento (
    central     VARCHAR(255),
    hora        INT,
    kwh         FLOAT,
    fecha       DATE,
    tipo        VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- =============================================================================
-- TABLAS DE MAPEO (lookup manuales, se poblan fuera de este script)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- empresa2
-- Propósito: mapea el nombre de empresa tal como viene en los archivos fuente
--            al nombre oficial en balance.empresa.
-- Usada en : revisar/cargar de barras, retiroregulado, compensacion, sscc,
--            inyecciones (via revisar_inyecciones con empresa2 implícita).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_balance.empresa2 (
    col_7           VARCHAR(255)  NOT NULL COMMENT 'Nombre en archivo fuente',
    nombreempresa   VARCHAR(255)           COMMENT 'Nombre en balance.empresa',
    PRIMARY KEY (col_7)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- -----------------------------------------------------------------------------
-- barra2
-- Propósito: mapea el nombre de barra CMG (nombre_barra_cmg) al nombre
--            oficial en balance.barra.
-- Usada en : cargar_cmg, revisar_inyecciones.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_balance.barra2 (
    col_1           VARCHAR(255)  NOT NULL COMMENT 'Nombre CMG en archivo fuente',
    nombrebarra     VARCHAR(255)           COMMENT 'Nombre en balance.barra',
    PRIMARY KEY (col_1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- -----------------------------------------------------------------------------
-- descripcion2
-- Propósito: mapea la columna "descripcion" del balance (tipo de punto de
--            medida) al id/descripcion oficial en balance.descripcion.
-- Usada en : revisar_balance, cargar_balance (relacion), revisar_inyecciones.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_balance.descripcion2 (
    col_8           VARCHAR(255)  NOT NULL COMMENT 'Descripción en archivo fuente',
    descripcion     VARCHAR(255)           COMMENT 'Descripción en balance.descripcion',
    PRIMARY KEY (col_8)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- -----------------------------------------------------------------------------
-- unidadgen2
-- Propósito: mapea el nombre de central tal como viene en los archivos fuente
--            al nombre oficial en balance.unidadgeneracion.
-- Usada en : cargar_sobrecostos (cv_importado y sobrecostos),
--            cargar_vertimientos, revisar_sobrecostos, revisar_vertimiento.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_balance.unidadgen2 (
    central                     VARCHAR(255)  NOT NULL COMMENT 'Nombre en archivo fuente',
    central_unidadgeneracion    VARCHAR(255)           COMMENT 'Nombre en balance.unidadgeneracion',
    PRIMARY KEY (central)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- =============================================================================
-- FIN DEL SCRIPT
-- =============================================================================
