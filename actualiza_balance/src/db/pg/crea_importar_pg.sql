-- =============================================================================
-- crea_importar_pg.sql
-- Crea el schema staging 'importar' y todas sus tablas en PostgreSQL.
--
-- En MySQL el staging vive en la BD 'importar_balance' (accesible como 'importar_mcp.tabla').
-- En PostgreSQL se replica esta estructura con el schema 'importar' dentro
-- de la misma BD que las tablas definitivas (ej: BD 'balance').
--
-- Las referencias mercado_corto_plazo.tabla e importar_mcp.tabla funcionan igual en ambos motores
-- porque en PostgreSQL 'schema.tabla' usa la misma notación.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Creación del schema staging
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS importar_mcp;


-- =============================================================================
-- TABLAS DE DATOS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- cmg
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_mcp.cmg (
    nombre_barra        VARCHAR(50),
    tension             INTEGER,
    nombre_barra_cmg    VARCHAR(50),
    cuarto_hora         INTEGER,
    cmg_peso_kwh        NUMERIC(10,5),
    cmg_dolar_mwh       NUMERIC(10,5),
    dolar               NUMERIC(10,2)
);


-- -----------------------------------------------------------------------------
-- barras_importadas
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_mcp.barras_importadas (
    nombre_barra        VARCHAR(50),
    tension             INTEGER,
    barra_infotecnica   INTEGER,
    codigo_cne          VARCHAR(50),
    nombre_barra_cne    VARCHAR(100),
    subestacion         VARCHAR(100),
    comuna              VARCHAR(50),
    calificacion        VARCHAR(100),
    zona_concesion      VARCHAR(50),
    zona_transicion     VARCHAR(100),
    empresa             VARCHAR(255)
);


-- -----------------------------------------------------------------------------
-- balance
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_mcp.balance (
    nombre_barra        VARCHAR(100),
    tension             INTEGER,
    clave               VARCHAR(255),
    nro_lt              VARCHAR(50),
    cuarto_hora         INTEGER,
    fecha_medicion      TIMESTAMP,
    rut                 VARCHAR(20),
    nombre_corto        VARCHAR(100),
    descripcion         VARCHAR(255),
    id_contrato         VARCHAR(50),
    tipo                VARCHAR(50),
    precio              VARCHAR(50),
    zona                VARCHAR(100),
    medida_1            NUMERIC(25,5),
    medida_2            NUMERIC(25,5),
    cmg_pesos_kwh       NUMERIC(20,5),
    valorizado_pesos    NUMERIC(20,5)
);


-- -----------------------------------------------------------------------------
-- contratos
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_mcp.contratos (
    nombre_barra        VARCHAR(255),
    tension             INTEGER,
    clave               VARCHAR(255)  NOT NULL,
    rut                 VARCHAR(20),
    nombre_corto        VARCHAR(255),
    descripcion         VARCHAR(255),
    id_contrato         INTEGER,
    tipo                VARCHAR(50),
    cuarto_hora         INTEGER,
    medida_1            NUMERIC(40,20),
    cmg_peso_kwh        NUMERIC(40,20),
    valorizado_pesos    NUMERIC(40,20)
);


-- -----------------------------------------------------------------------------
-- retiroregulado
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_mcp.retiroregulado (
    bloque_regulado     VARCHAR(100),
    suministrador       VARCHAR(100),
    kwh_ps1             FLOAT,
    "%_ps1"             FLOAT,
    kwh_ps2             FLOAT,
    "%_ps2"             FLOAT,
    fisico_kwh          FLOAT,
    monetario           FLOAT
);


-- -----------------------------------------------------------------------------
-- compensacion
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_mcp.compensacion (
    hora_mensual            INTEGER,
    suministrador           VARCHAR(100),
    prorrata_suministrador  NUMERIC(40,20),
    diferencia_horaria      NUMERIC(40,20),
    compensacion            NUMERIC(40,20)
);


-- -----------------------------------------------------------------------------
-- inyecciones
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_mcp.inyecciones (
    cuarto_hora             INTEGER,
    clave                   VARCHAR(255),
    rut                     VARCHAR(20),
    nombre_corto            VARCHAR(255),
    descripcion             VARCHAR(255),
    nombre_barra_cmg        VARCHAR(255),
    tipo                    VARCHAR(10),
    precio_pncp             NUMERIC(40,20),
    medida_1                NUMERIC(40,20),
    cmg_peso_kwh            NUMERIC(40,20),
    valorizado_cmg          NUMERIC(40,20),
    valorizado_pncp         NUMERIC(40,20),
    diferencia_pncp_cmg     NUMERIC(40,20)
);


-- -----------------------------------------------------------------------------
-- cv_importado
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_mcp.cv_importado (
    fecha           DATE          NOT NULL,
    hora            INTEGER       NOT NULL,
    unidadgen       VARCHAR(255)  NOT NULL,
    cv_usd_mwh      FLOAT
);


-- -----------------------------------------------------------------------------
-- sobrecostos
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_mcp.sobrecostos (
    fecha           DATE          NOT NULL,
    hora            INTEGER       NOT NULL,
    tipo            VARCHAR(50),
    unidadgen       VARCHAR(255)  NOT NULL,
    sobrecosto_clp  FLOAT,
    zona_pago       VARCHAR(50),
    gen             FLOAT,
    cons_propio     FLOAT,
    cv              FLOAT,
    cmg             FLOAT,
    sscc            TEXT
);


-- -----------------------------------------------------------------------------
-- sscc_rt
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_mcp.sscc_rt (
    concepto    VARCHAR(255),
    empresa     VARCHAR(255),
    recibe      FLOAT,
    paga        FLOAT,
    sen         FLOAT
);


-- -----------------------------------------------------------------------------
-- sscc_infra
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_mcp.sscc_infra (
    empresa         VARCHAR(255),
    remuneracion    FLOAT,
    recaudacion     FLOAT,
    neto            FLOAT
);


-- -----------------------------------------------------------------------------
-- vertimiento
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS importar_mcp.vertimiento (
    central     VARCHAR(255),
    hora        INTEGER,
    kwh         FLOAT,
    fecha       DATE,
    tipo        VARCHAR(50)
);


-- =============================================================================
-- TABLAS DE MAPEO (lookup manuales, se poblan fuera de este script)
-- =============================================================================

CREATE TABLE IF NOT EXISTS importar_mcp.empresa2 (
    col_7           VARCHAR(255)  NOT NULL,
    nombreempresa   VARCHAR(255),
    PRIMARY KEY (col_7)
);

CREATE TABLE IF NOT EXISTS importar_mcp.barra2 (
    col_1           VARCHAR(255)  NOT NULL,
    nombrebarra     VARCHAR(255),
    PRIMARY KEY (col_1)
);

CREATE TABLE IF NOT EXISTS importar_mcp.descripcion2 (
    col_8           VARCHAR(255)  NOT NULL,
    descripcion     VARCHAR(255),
    PRIMARY KEY (col_8)
);

CREATE TABLE IF NOT EXISTS importar_mcp.unidadgen2 (
    central                     VARCHAR(255)  NOT NULL,
    central_unidadgeneracion    VARCHAR(255),
    PRIMARY KEY (central)
);


-- =============================================================================
-- FIN DEL SCRIPT
-- =============================================================================
