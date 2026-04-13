-- PostgreSQL schema para la base de datos: mercado_corto_plazo
-- Migrado desde MariaDB/MySQL (base: balance)
-- Generado: 2026-04-11
--
-- Notas de migración:
--   - AUTO_INCREMENT → SERIAL / BIGSERIAL
--   - tinyint(1) → BOOLEAN  (1 → TRUE, 0 → FALSE)
--   - float → REAL,  decimal(p,s) → NUMERIC(p,s)
--   - datetime → TIMESTAMP
--   - GENERATED ALWAYS AS: year/month/quarter/dayofweek → EXTRACT(...)
--   - Índices inline → CREATE INDEX separados
--   - Columnas '%_ps1', '%_ps2' renombradas a pct_ps1, pct_ps2 (% no es válido en PG)
--   - Nombres con mayúsculas/camelCase preservados entre comillas dobles

CREATE DATABASE mercado_corto_plazo
    ENCODING 'UTF8';

\connect mercado_corto_plazo

CREATE SCHEMA IF NOT EXISTS mercado_corto_plazo;
SET search_path TO mercado_corto_plazo;

-- ============================================================
-- TABLAS BASE (sin dependencias de FK)
-- ============================================================

DROP TABLE IF EXISTS codigo_territorio CASCADE;
CREATE TABLE codigo_territorio (
    idregion            VARCHAR(10)  NOT NULL,
    nombre_region       VARCHAR(50)  NOT NULL,
    abreviatura_region  VARCHAR(10)  NOT NULL,
    idprovincia         VARCHAR(10)  NOT NULL,
    nombre_provincia    VARCHAR(30)  NOT NULL,
    idcomuna            VARCHAR(10)  NOT NULL,
    nombre_comuna       VARCHAR(20)  NOT NULL,
    PRIMARY KEY (idcomuna)
);
CREATE INDEX idx_ct_idregion ON codigo_territorio (idregion);

-- ----------------------------------------

DROP TABLE IF EXISTS empresa CASCADE;
CREATE TABLE empresa (
    id_empresa  SERIAL,
    rut_empresa VARCHAR(13) NOT NULL,
    nombre      TEXT,
    PRIMARY KEY (rut_empresa),
    UNIQUE (id_empresa)
);

-- ----------------------------------------

DROP TABLE IF EXISTS version CASCADE;
CREATE TABLE version (
    id_version  INTEGER NOT NULL,
    periodo     DATE,
    tipo        VARCHAR(255),
    nombre      VARCHAR(255),
    año         INTEGER GENERATED ALWAYS AS (EXTRACT(YEAR  FROM periodo)::INTEGER) STORED,
    mes         INTEGER GENERATED ALWAYS AS (EXTRACT(MONTH FROM periodo)::INTEGER) STORED,
    PRIMARY KEY (id_version),
    UNIQUE (periodo, tipo)
);
CREATE INDEX idx_version_periodo ON version (periodo);
CREATE INDEX idx_version_año     ON version (año);
CREATE INDEX idx_version_mes     ON version (mes);

-- ============================================================
-- TABLAS CON DEPENDENCIAS DE PRIMER NIVEL
-- ============================================================

DROP TABLE IF EXISTS subestacion CASCADE;
CREATE TABLE subestacion (
    id_subestacion          SERIAL,
    nombre                  VARCHAR(50)  NOT NULL,
    idregion                VARCHAR(10)  NOT NULL,
    idprovincia             VARCHAR(10)  NOT NULL,
    idcomuna                VARCHAR(10)  NOT NULL,
    tipoconfiguracion       VARCHAR(50),
    entrada_en_operacion    VARCHAR(10),
    coordenada_este         VARCHAR(20),
    coordenada_norte        VARCHAR(20),
    huso                    VARCHAR(10),
    observacion             VARCHAR(30),
    PRIMARY KEY (id_subestacion),
    CONSTRAINT fk_subestacion_codigoterritorio
        FOREIGN KEY (idcomuna) REFERENCES codigo_territorio (idcomuna)
        ON DELETE NO ACTION ON UPDATE NO ACTION
);

-- ----------------------------------------

DROP TABLE IF EXISTS hora_mensual CASCADE;
CREATE TABLE hora_mensual (
    id_hora     BIGINT  NOT NULL,
    id_version  INTEGER,
    cuarto_hora INTEGER,
    dia         INTEGER,
    hora        INTEGER,
    minuto      INTEGER,
    fecha_hora  TIMESTAMP,
    -- Columnas generadas (equivalentes a las funciones MySQL)
    trimestre   SMALLINT GENERATED ALWAYS AS (EXTRACT(QUARTER FROM fecha_hora)::SMALLINT) STORED,
    -- dow: 0=domingo … 6=sábado (igual que MySQL dayofweek - 1)
    dow         SMALLINT GENERATED ALWAYS AS (EXTRACT(DOW    FROM fecha_hora)::SMALLINT) STORED,
    año         SMALLINT GENERATED ALWAYS AS (EXTRACT(YEAR   FROM fecha_hora)::SMALLINT) STORED,
    mes         SMALLINT GENERATED ALWAYS AS (EXTRACT(MONTH  FROM fecha_hora)::SMALLINT) STORED,
    PRIMARY KEY (id_hora),
    UNIQUE (id_version, dia, hora, minuto),
    CONSTRAINT fk_hora_version
        FOREIGN KEY (id_version) REFERENCES version (id_version)
);
CREATE INDEX idx_hm_hora            ON hora_mensual (hora);
CREATE INDEX idx_hm_version_minuto  ON hora_mensual (id_version, minuto, cuarto_hora);
CREATE INDEX idx_hm_idv_hora        ON hora_mensual (id_version, cuarto_hora, hora);
CREATE INDEX idx_hm_fecha_hora      ON hora_mensual (fecha_hora);
CREATE INDEX idx_hm_version_fecha   ON hora_mensual (id_version, fecha_hora);
CREATE INDEX idx_hm_año_mes         ON hora_mensual (año, mes);
CREATE INDEX idx_hm_version_año_mes ON hora_mensual (id_version, año, mes);

-- ============================================================
-- TABLAS CON DEPENDENCIAS DE SEGUNDO NIVEL
-- ============================================================

DROP TABLE IF EXISTS barras CASCADE;
CREATE TABLE barras (
    nombre          VARCHAR(255),
    tension         REAL,
    nombre_cmg      VARCHAR(255),
    subestacion     TEXT,
    id_infotecnica  INTEGER,
    calificacion    TEXT,
    id_empresa      INTEGER,
    id_barra        SERIAL,
    vigente         BOOLEAN  DEFAULT TRUE,
    observacion     TEXT,
    barra_troncal   BOOLEAN  DEFAULT FALSE,
    id_subestacion  INTEGER,
    PRIMARY KEY (id_barra),
    CONSTRAINT fk_barra_subestacion
        FOREIGN KEY (id_subestacion) REFERENCES subestacion (id_subestacion)
);
CREATE INDEX idx_barra_subestacion ON barras (id_subestacion);

-- ----------------------------------------

DROP TABLE IF EXISTS central CASCADE;
CREATE TABLE central (
    id_central                  INTEGER NOT NULL,
    nombre_central              VARCHAR(255),
    id_infotecnica              INTEGER,
    coordinado                  VARCHAR(255),
    tipo                        VARCHAR(80),
    subtipo                     VARCHAR(80),
    punto_conexion_sen          VARCHAR(255),
    punto_conexion_sen_limpio   VARCHAR(255),
    id_subestacion              INTEGER,
    tecnologia                  VARCHAR(120),
    id_empresa                  INTEGER,
    observacion                 TEXT,
    PRIMARY KEY (id_central),
    CONSTRAINT fk_centrales_subestacion
        FOREIGN KEY (id_subestacion) REFERENCES subestacion (id_subestacion)
);
CREATE INDEX idx_centrales_id_subestacion ON central (id_subestacion);

-- ============================================================
-- TABLAS CON DEPENDENCIAS DE TERCER NIVEL
-- ============================================================

DROP TABLE IF EXISTS unidad_generacion CASCADE;
CREATE TABLE unidad_generacion (
    id_unidad_generacion    INTEGER NOT NULL,
    "Nombre"                VARCHAR(255),
    id_central              INTEGER,
    "Combustible"           VARCHAR(255),
    PRIMARY KEY (id_unidad_generacion),
    CONSTRAINT fk_unidad_central
        FOREIGN KEY (id_central) REFERENCES central (id_central)
);
CREATE INDEX idx_ug_nombre    ON unidad_generacion ("Nombre");
CREATE INDEX idx_ug_id_central ON unidad_generacion (id_central);

-- ----------------------------------------

DROP TABLE IF EXISTS medidores CASCADE;
CREATE TABLE medidores (
    id_medidor  SERIAL,
    clave       VARCHAR(255) NOT NULL,
    id_barra    INTEGER,
    nro_lt      NUMERIC(18,5),
    clave_lt    VARCHAR(255),
    "idEmpresa" VARCHAR(13),
    tipo1       VARCHAR(50),
    zona        VARCHAR(100),
    PRIMARY KEY (id_medidor),
    CONSTRAINT fk_medidor_barra
        FOREIGN KEY (id_barra) REFERENCES barras (id_barra)
);
CREATE INDEX idx_medidor_barra ON medidores (id_barra);

-- ============================================================
-- TABLAS CON DEPENDENCIAS DE CUARTO NIVEL
-- ============================================================

DROP TABLE IF EXISTS cmg CASCADE;
CREATE TABLE cmg (
    id_cmg          BIGSERIAL,
    id_version      INTEGER NOT NULL,
    id_hora         BIGINT,
    id_barra        INTEGER NOT NULL,
    "CMG_PESO_KWH"  REAL,
    "CMG_DOLAR_MWH" REAL    DEFAULT 0,
    dolar           REAL    DEFAULT 0,
    PRIMARY KEY (id_cmg),
    CONSTRAINT fk_cmg_hora
        FOREIGN KEY (id_hora) REFERENCES hora_mensual (id_hora)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT fk_cmg_id_barra
        FOREIGN KEY (id_barra) REFERENCES barras (id_barra)
);
CREATE INDEX idx_cmg_barra     ON cmg (id_barra);
CREATE INDEX idx_cmg_version   ON cmg (id_version);
CREATE INDEX idx_cmg_hora_barra ON cmg (id_hora, id_barra);

-- ----------------------------------------

DROP TABLE IF EXISTS contratos_financieros CASCADE;
CREATE TABLE contratos_financieros (
    id_transaccion  BIGSERIAL,
    idversion       INTEGER      NOT NULL,
    clave           VARCHAR(255) NOT NULL,
    id_hora_old     INTEGER,
    energia_kwh     REAL,
    cmg_clp_kwh     REAL,
    valorizado_clp  REAL,
    rut_empresa     VARCHAR(50),
    id_barra        INTEGER,
    transaccion     TEXT,
    observacion     TEXT,
    id_contrato     INTEGER,
    id_hora         BIGINT,
    PRIMARY KEY (id_transaccion),
    CONSTRAINT fk_contratos_hora
        FOREIGN KEY (id_hora) REFERENCES hora_mensual (id_hora)
);
CREATE INDEX idx_cf_version_hora_old ON contratos_financieros (idversion, id_hora_old);
CREATE INDEX idx_cf_hora             ON contratos_financieros (id_hora);

-- ----------------------------------------

DROP TABLE IF EXISTS contratos_fisicos CASCADE;
CREATE TABLE contratos_fisicos (
    idversion       INTEGER      NOT NULL,
    id_contrato     INTEGER,
    observacion     TEXT,
    clave           VARCHAR(255) NOT NULL,
    rut_empresa     VARCHAR(50),
    id_barra        INTEGER,
    transaccion     TEXT,
    id_hora         BIGINT,
    cmg_clp_kwh     REAL,
    energia_kwh     REAL,
    valorizado_clp  REAL,
    id_transaccion  BIGSERIAL,
    PRIMARY KEY (id_transaccion),
    CONSTRAINT fk_contratos_fisicos_empresa
        FOREIGN KEY (rut_empresa) REFERENCES empresa (rut_empresa),
    CONSTRAINT fk_contratos_fisicos_hora
        FOREIGN KEY (id_hora) REFERENCES hora_mensual (id_hora)
);
CREATE INDEX idx_cfis_barra   ON contratos_fisicos (id_barra);
CREATE INDEX idx_cfis_empresa ON contratos_fisicos (rut_empresa);
CREATE INDEX idx_cfis_hora    ON contratos_fisicos (id_hora);

-- ----------------------------------------

DROP TABLE IF EXISTS cv CASCADE;
CREATE TABLE cv (
    "idVersion"     INTEGER NOT NULL,
    hora_mensual    INTEGER NOT NULL,
    id_hora         BIGINT,
    "idUnidadgen"   INTEGER NOT NULL,
    cv_usd_mwh      REAL,
    PRIMARY KEY ("idVersion", hora_mensual, "idUnidadgen"),
    CONSTRAINT cv_fk_unidad
        FOREIGN KEY ("idUnidadgen") REFERENCES unidad_generacion (id_unidad_generacion),
    CONSTRAINT fk_cv_hora
        FOREIGN KEY (id_hora) REFERENCES hora_mensual (id_hora)
        ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE INDEX idx_cv_unidadgen ON cv ("idUnidadgen");
CREATE INDEX idx_cv_hora      ON cv (id_hora);

-- ----------------------------------------

DROP TABLE IF EXISTS gx_real CASCADE;
CREATE TABLE gx_real (
    id_generacion       BIGSERIAL,
    id_central          INTEGER      NOT NULL,
    nombre_unidadgen    VARCHAR(255),
    id_version          INTEGER      NOT NULL,
    inyeccion_retiro    NUMERIC(18,6),
    id_hora             BIGINT,
    subtipo             VARCHAR(255),
    PRIMARY KEY (id_generacion),
    CONSTRAINT fk_gx_real_centrales
        FOREIGN KEY (id_central) REFERENCES central (id_central),
    CONSTRAINT fk_gxreal_horamensual
        FOREIGN KEY (id_hora) REFERENCES hora_mensual (id_hora)
);
CREATE INDEX idx_gx_real_id_central       ON gx_real (id_central);
CREATE INDEX idx_gx_real_hora             ON gx_real (id_hora);
CREATE INDEX idx_gx_real_version_central  ON gx_real (id_version, id_central);
CREATE INDEX idx_gx_real_version_unidadgen ON gx_real (id_version, nombre_unidadgen);
CREATE INDEX idx_gx_real_central_hora     ON gx_real (id_central, id_hora);

-- ----------------------------------------

DROP TABLE IF EXISTS pe_inyecciones CASCADE;
CREATE TABLE pe_inyecciones (
    id_version              INTEGER,
    clave                   VARCHAR(255) NOT NULL,
    cuarto_hora             INTEGER      NOT NULL,
    precio_nudo             NUMERIC(40,20),
    valorizado_pnudo        NUMERIC(40,20),
    diferencia_pnudo_cmg    NUMERIC(40,20),
    energia_sobre_9mwh      NUMERIC(40,20) DEFAULT 0,
    medida_15min_ajustada   NUMERIC(40,20) DEFAULT 0,
    observacion             TEXT          DEFAULT '',
    id_pe_inyeccion         SERIAL,
    PRIMARY KEY (id_pe_inyeccion)
);

-- ----------------------------------------

DROP TABLE IF EXISTS pe_compensacion CASCADE;
CREATE TABLE pe_compensacion (
    "idVersion"             INTEGER      NOT NULL,
    hora_mensual            INTEGER      NOT NULL,
    "idEmpresa"             VARCHAR(13)  NOT NULL DEFAULT '',
    prorrata_suministrador  NUMERIC(40,20),
    diferencia_horaria      NUMERIC(40,20),
    compensacion            NUMERIC(40,20),
    PRIMARY KEY ("idVersion", hora_mensual, "idEmpresa"),
    CONSTRAINT fk_pe_compensacion_empresa
        FOREIGN KEY ("idEmpresa") REFERENCES empresa (rut_empresa)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT fk_pe_compensacion_version
        FOREIGN KEY ("idVersion") REFERENCES version (id_version)
);

-- ----------------------------------------

DROP TABLE IF EXISTS inyecciones CASCADE;
CREATE TABLE inyecciones (
    id_version          INTEGER      NOT NULL,
    clave               VARCHAR(255) NOT NULL,
    cuarto_hora         INTEGER      NOT NULL,
    "MedidaHoraria2"    NUMERIC(25,5),
    "MedidaHoraria"     NUMERIC(25,5),
    "CMG_PESO_KWH"      NUMERIC(20,5),
    "VALORIZADO_PESOS"  NUMERIC(20,5),
    rut_empresa         VARCHAR(13),
    id_hora             BIGINT,
    id_pe_inyeccion     INTEGER,
    id_medidor          INTEGER,
    PRIMARY KEY (id_version, clave, cuarto_hora),
    CONSTRAINT fk_inyecciones_empresa
        FOREIGN KEY (rut_empresa) REFERENCES empresa (rut_empresa),
    CONSTRAINT fk_inyecciones_hora
        FOREIGN KEY (id_hora) REFERENCES hora_mensual (id_hora),
    CONSTRAINT fk_inyecciones_pe
        FOREIGN KEY (id_pe_inyeccion) REFERENCES pe_inyecciones (id_pe_inyeccion),
    CONSTRAINT fk_inyecciones_medidor
        FOREIGN KEY (id_medidor) REFERENCES medidores (id_medidor)
);
CREATE INDEX idx_inyecciones_version       ON inyecciones (id_version);
CREATE INDEX idx_inyecciones_version_clave ON inyecciones (id_version, clave);
CREATE INDEX idx_inyecciones_rut_empresa   ON inyecciones (rut_empresa);
CREATE INDEX idx_inyecciones_hora          ON inyecciones (id_hora);
CREATE INDEX idx_inyecciones_pe            ON inyecciones (id_pe_inyeccion);
CREATE INDEX idx_inyecciones_medidor       ON inyecciones (id_medidor);

-- ----------------------------------------

DROP TABLE IF EXISTS retiro CASCADE;
CREATE TABLE retiro (
    id_version          INTEGER      NOT NULL,
    clave               VARCHAR(255) NOT NULL,
    cuarto_hora         INTEGER      NOT NULL,
    "MedidaHoraria2"    NUMERIC(25,5),
    "MedidaHoraria"     NUMERIC(25,5),
    "CMG_PESO_KWH"      NUMERIC(20,5),
    "VALORIZADO_PESOS"  NUMERIC(20,5),
    id_medidor          INTEGER,
    id_hora             BIGINT,
    PRIMARY KEY (id_version, clave, cuarto_hora),
    CONSTRAINT fk_retiro_hora
        FOREIGN KEY (id_hora) REFERENCES hora_mensual (id_hora),
    CONSTRAINT fk_retiro_medidor
        FOREIGN KEY (id_medidor) REFERENCES medidores (id_medidor)
);
CREATE INDEX idx_retiro_version_clave ON retiro (id_version, clave);
CREATE INDEX idx_retiro_version_cuarto ON retiro (id_version, cuarto_hora);
CREATE INDEX idx_retiro_version        ON retiro (id_version);
CREATE INDEX idx_retiro_medidor        ON retiro (id_medidor);
CREATE INDEX idx_retiro_hora           ON retiro (id_hora);

-- ----------------------------------------

-- Nota: columnas '%_ps1' y '%_ps2' renombradas a pct_ps1 y pct_ps2
--       ya que '%' no es válido en identificadores PostgreSQL sin comillas.
DROP TABLE IF EXISTS retiro_regulado CASCADE;
CREATE TABLE retiro_regulado (
    id_retiro_regulado  SERIAL,
    id_version          INTEGER     NOT NULL,
    bloque_regulado     VARCHAR(10),
    idempresa_br        INTEGER     NOT NULL,
    idempresa_sum       INTEGER     NOT NULL,
    kwh_ps1             REAL,
    pct_ps1             REAL,
    kwh_ps2             REAL,
    pct_ps2             REAL,
    fisico_kwh          REAL,
    monetario           REAL,
    PRIMARY KEY (id_retiro_regulado),
    CONSTRAINT fk_retiro_regulado_br
        FOREIGN KEY (idempresa_br) REFERENCES empresa (id_empresa),
    CONSTRAINT fk_retiro_regulado_sum
        FOREIGN KEY (idempresa_sum) REFERENCES empresa (id_empresa),
    CONSTRAINT fk_retiro_regulado_version
        FOREIGN KEY (id_version) REFERENCES version (id_version)
);
CREATE INDEX idx_rr_empresa_br  ON retiro_regulado (idempresa_br);
CREATE INDEX idx_rr_empresa_sum ON retiro_regulado (idempresa_sum);

-- ----------------------------------------

DROP TABLE IF EXISTS sobrecostos CASCADE;
CREATE TABLE sobrecostos (
    "idVersion"     INTEGER NOT NULL,
    hora_mensual    INTEGER NOT NULL,
    id_hora         BIGINT,
    "idUnidadgen"   INTEGER NOT NULL,
    tipo            TEXT,
    sobrecosto_clp  REAL,
    zona_pago       TEXT,
    gen             REAL,
    cons_propio     REAL,
    cv              REAL,
    cmg             REAL,
    sscc            TEXT,
    PRIMARY KEY ("idVersion", hora_mensual, "idUnidadgen"),
    CONSTRAINT fk_sobrecostos_hora
        FOREIGN KEY (id_hora) REFERENCES hora_mensual (id_hora)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT fk_sobrecostos_unidad
        FOREIGN KEY ("idUnidadgen") REFERENCES unidad_generacion (id_unidad_generacion)
);
CREATE INDEX idx_sobrecostos_unidadgen ON sobrecostos ("idUnidadgen");
CREATE INDEX idx_sobrecostos_hora      ON sobrecostos (id_hora);

-- ----------------------------------------

DROP TABLE IF EXISTS sscc_infra CASCADE;
CREATE TABLE sscc_infra (
    "idVersion"     INTEGER     NOT NULL,
    "idEmpresa"     VARCHAR(13) NOT NULL DEFAULT '',
    remuneracion    REAL,
    recaudacion     REAL,
    neto            REAL,
    PRIMARY KEY ("idVersion", "idEmpresa"),
    CONSTRAINT fk_sscc_infra_empresa
        FOREIGN KEY ("idEmpresa") REFERENCES empresa (rut_empresa)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT fk_sscc_infra_version
        FOREIGN KEY ("idVersion") REFERENCES version (id_version)
);

-- ----------------------------------------

-- Nota: clave compuesta en MySQL era (idVersion, concepto(100), idEmpresa)
--       usando prefijo de 100 chars. En PostgreSQL TEXT puede ser PK completo.
DROP TABLE IF EXISTS sscc_rt CASCADE;
CREATE TABLE sscc_rt (
    "idVersion"     INTEGER     NOT NULL,
    concepto        TEXT        NOT NULL,
    "idEmpresa"     VARCHAR(13) NOT NULL DEFAULT '',
    recibe          REAL,
    paga            REAL,
    sen             REAL,
    PRIMARY KEY ("idVersion", concepto, "idEmpresa"),
    CONSTRAINT fk_sscc_rt_empresa
        FOREIGN KEY ("idEmpresa") REFERENCES empresa (rut_empresa)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT fk_sscc_rt_version
        FOREIGN KEY ("idVersion") REFERENCES version (id_version)
);

-- ----------------------------------------

DROP TABLE IF EXISTS transmision CASCADE;
CREATE TABLE transmision (
    id_version          INTEGER      NOT NULL,
    clave               VARCHAR(255) NOT NULL,
    cuarto_hora         INTEGER      NOT NULL,
    "MedidaHoraria2"    NUMERIC(25,5),
    "MedidaHoraria"     NUMERIC(25,5),
    "CMG_PESO_KWH"      NUMERIC(20,5),
    "VALORIZADO_PESOS"  NUMERIC(20,5),
    id_hora             BIGINT,
    id_medidor          INTEGER,
    PRIMARY KEY (id_version, clave, cuarto_hora),
    CONSTRAINT fk_transmision_hora
        FOREIGN KEY (id_hora) REFERENCES hora_mensual (id_hora)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT fk_transmision_medidor
        FOREIGN KEY (id_medidor) REFERENCES medidores (id_medidor)
        ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE INDEX idx_transmision_hora    ON transmision (id_hora);
CREATE INDEX idx_transmision_medidor ON transmision (id_medidor);

-- ----------------------------------------

DROP TABLE IF EXISTS vertimiento CASCADE;
CREATE TABLE vertimiento (
    id_vertimiento      BIGSERIAL,
    id_version          INTEGER NOT NULL,
    id_central          INTEGER,
    id_unidadgen        INTEGER,
    id_hora             BIGINT,
    tipo                TEXT    NOT NULL,
    nombre_unidadgen    VARCHAR(255),
    vertimiento         REAL,
    PRIMARY KEY (id_vertimiento),
    CONSTRAINT fk_vertimiento_central
        FOREIGN KEY (id_central) REFERENCES central (id_central),
    CONSTRAINT fk_vertimiento_hora
        FOREIGN KEY (id_hora) REFERENCES hora_mensual (id_hora)
);
CREATE INDEX idx_vertimiento_version ON vertimiento (id_version);
CREATE INDEX idx_vertimiento_central ON vertimiento (id_central);
CREATE INDEX idx_vertimiento_hora    ON vertimiento (id_hora);

-- ============================================================
-- VISTAS
-- ============================================================

CREATE OR REPLACE VIEW cmg_barra AS
SELECT
    v.nombre            AS periodo_datos,
    hm.fecha_hora       AS fecha_hora,
    b.nombre            AS nombre_barra,
    b.tension           AS tension,
    b.nombre_cmg        AS nombre_cmg,
    c."CMG_PESO_KWH"    AS "CMG_PESO_KWH",
    c."CMG_DOLAR_MWH"   AS "CMG_DOLAR_MWH"
FROM cmg c
JOIN version v       ON c.id_version = v.id_version
JOIN hora_mensual hm ON c.id_version = hm.id_version AND c.id_hora = hm.id_hora
JOIN barras b        ON c.id_barra = b.id_barra;

-- ----------------------------------------

CREATE OR REPLACE VIEW gx_real_retiro AS
SELECT
    v.nombre                AS periodo_datos,
    h.fecha_hora            AS fecha_hora,
    b.nombre                AS nombre_barra,
    b.tension               AS tension,
    b.nombre_cmg            AS nombre_cmg,
    c.nombre_central        AS nombre_central,
    c.tipo                  AS tipo_central,
    g.inyeccion_retiro      AS retiro
FROM gx_real g
JOIN hora_mensual h  ON g.id_hora = h.id_hora
JOIN central c       ON g.id_central = c.id_central
JOIN version v       ON g.id_version = v.id_version
JOIN subestacion s   ON c.id_subestacion = s.id_subestacion
JOIN barras b        ON s.id_subestacion = b.id_subestacion
WHERE g.inyeccion_retiro < 0;

-- ----------------------------------------

CREATE OR REPLACE VIEW inyeccion_compensacion AS
SELECT
    v.id_version,
    e.nombre                    AS nombre_empresa,
    p.cuarto_hora,
    p.precio_nudo,
    p.valorizado_pnudo,
    p.diferencia_pnudo_cmg,
    p.energia_sobre_9mwh,
    p.medida_15min_ajustada,
    pc.prorrata_suministrador,
    pc.diferencia_horaria
FROM pe_inyecciones p
JOIN version v          ON p.id_version = v.id_version
JOIN medidores m        ON p.clave = m.clave
JOIN empresa e          ON m."idEmpresa" = e.rut_empresa
JOIN pe_compensacion pc ON p.id_version  = pc."idVersion"
                       AND p.cuarto_hora = pc.hora_mensual
                       AND e.rut_empresa = pc."idEmpresa";

-- ----------------------------------------

CREATE OR REPLACE VIEW proporcion_renovables AS
WITH renovables AS (
    SELECT
        hor.año                         AS año,
        hor.mes                         AS mes,
        cen.tipo                        AS tipo_tecnologia,
        gx.subtipo                      AS subtipo,
        SUM(gx.inyeccion_retiro)        AS total_inyeccion
    FROM gx_real gx
    JOIN central cen      ON gx.id_central = cen.id_central
    JOIN hora_mensual hor ON gx.id_hora    = hor.id_hora
    WHERE cen.tipo IN ('Hidroeléctricas', 'Geotérmica', 'Solar', 'Eólicas', 'Mareomotriz')
       OR (cen.tipo = 'Termoeléctricas' AND gx.subtipo IN ('Biomasa', 'BioGas'))
    GROUP BY hor.año, hor.mes, cen.tipo, gx.subtipo
),
total_sistema AS (
    SELECT
        hor.año                         AS año,
        hor.mes                         AS mes,
        SUM(gx.inyeccion_retiro)        AS total_inyeccion
    FROM gx_real gx
    JOIN hora_mensual hor ON gx.id_hora = hor.id_hora
    GROUP BY hor.año, hor.mes
)
SELECT
    r.año,
    r.mes,
    r.tipo_tecnologia,
    r.subtipo,
    r.total_inyeccion,
    t.total_inyeccion                                           AS total_sistema,
    ROUND(r.total_inyeccion / t.total_inyeccion * 100, 2)      AS proporcion_renovable
FROM renovables r
JOIN total_sistema t ON r.año = t.año AND r.mes = t.mes
ORDER BY r.año, r.mes, r.tipo_tecnologia, r.subtipo;

-- ----------------------------------------

CREATE OR REPLACE VIEW sscc AS
SELECT
    v.nombre            AS periodo_datos,
    e.nombre            AS nombre_empresa,
    e.rut_empresa,
    si.remuneracion     AS remuneracion_infra,
    si.recaudacion      AS recaudacion_infra,
    si.neto             AS neto_infra,
    sr.concepto,
    sr.recibe           AS recibe_RT,
    sr.paga             AS paga_RT,
    sr.sen              AS sen_RT,
    sr.sen + si.neto    AS total_neto_sen
FROM sscc_infra si
JOIN version v   ON si."idVersion" = v.id_version
JOIN empresa e   ON si."idEmpresa" = e.rut_empresa
JOIN sscc_rt sr  ON si."idVersion" = sr."idVersion"
               AND si."idEmpresa"  = sr."idEmpresa";
