-- MariaDB dump 10.19-11.3.1-MariaDB, for Win64 (AMD64)
--
-- Host: localhost    Database: balance
-- ------------------------------------------------------
-- Server version	11.3.1-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `barras`
--

DROP TABLE IF EXISTS `barras`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `barras` (
  `nombre` varchar(255) DEFAULT NULL,
  `tension` float DEFAULT NULL,
  `nombre_cmg` varchar(255) DEFAULT NULL,
  `subestacion` text DEFAULT NULL,
  `id_infotecnica` int(11) DEFAULT NULL,
  `calificacion` text DEFAULT NULL,
  `id_empresa` int(11) DEFAULT NULL,
  `id_barra` int(11) NOT NULL AUTO_INCREMENT,
  `vigente` tinyint(1) DEFAULT 1,
  `observacion` text DEFAULT NULL,
  `barra_troncal` tinyint(1) DEFAULT 0,
  `id_subestacion` int(11) DEFAULT NULL,
  PRIMARY KEY (`id_barra`),
  KEY `fk_barra_subestacion` (`id_subestacion`),
  CONSTRAINT `fk_barra_subestacion` FOREIGN KEY (`id_subestacion`) REFERENCES `subestacion` (`id_subestacion`)
) ENGINE=InnoDB AUTO_INCREMENT=1759 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `central`
--

DROP TABLE IF EXISTS `central`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `central` (
  `id_central` int(11) NOT NULL,
  `nombre_central` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_infotecnica` int(11) DEFAULT NULL,
  `coordinado` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tipo` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `subtipo` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `punto_conexion_sen` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `punto_conexion_sen_limpio` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_subestacion` int(11) DEFAULT NULL,
  `tecnologia` varchar(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_empresa` int(11) DEFAULT NULL,
  `observacion` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id_central`),
  KEY `idx_centrales_id_subestacion` (`id_subestacion`),
  CONSTRAINT `fk_centrales_subestacion` FOREIGN KEY (`id_subestacion`) REFERENCES `subestacion` (`id_subestacion`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cmg`
--

DROP TABLE IF EXISTS `cmg`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `cmg` (
  `id_cmg` bigint(20) NOT NULL AUTO_INCREMENT,
  `id_version` int(11) NOT NULL,
  `id_hora` bigint(20) DEFAULT NULL,
  `id_barra` int(11) NOT NULL,
  `CMG_PESO_KWH` float DEFAULT NULL,
  `CMG_DOLAR_MWH` float DEFAULT 0,
  `dolar` float DEFAULT 0,
  PRIMARY KEY (`id_cmg`),
  KEY `FK_cmg_barra` (`id_barra`) USING BTREE,
  KEY `FK_cmg_version` (`id_version`) USING BTREE,
  KEY `idx_hora_barra` (`id_hora`,`id_barra`),
  CONSTRAINT `fk_cmg_hora` FOREIGN KEY (`id_hora`) REFERENCES `hora_mensual` (`id_hora`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_cmg_id_barra` FOREIGN KEY (`id_barra`) REFERENCES `barras` (`id_barra`)
) ENGINE=InnoDB AUTO_INCREMENT=107479007 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Temporary table structure for view `cmg_barra`
--

DROP TABLE IF EXISTS `cmg_barra`;
/*!50001 DROP VIEW IF EXISTS `cmg_barra`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE VIEW `cmg_barra` AS SELECT
 1 AS `periodo_datos`,
  1 AS `fecha_hora`,
  1 AS `nombre_barra`,
  1 AS `tension`,
  1 AS `nombre_cmg`,
  1 AS `CMG_PESO_KWH`,
  1 AS `CMG_DOLAR_MWH` */;
SET character_set_client = @saved_cs_client;

--
-- Table structure for table `codigo_territorio`
--

DROP TABLE IF EXISTS `codigo_territorio`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `codigo_territorio` (
  `idregion` varchar(10) CHARACTER SET latin1 COLLATE latin1_general_ci NOT NULL,
  `nombre_region` varchar(50) CHARACTER SET latin1 COLLATE latin1_general_ci NOT NULL,
  `abreviatura_region` varchar(10) CHARACTER SET latin1 COLLATE latin1_general_ci NOT NULL,
  `idprovincia` varchar(10) CHARACTER SET latin1 COLLATE latin1_general_ci NOT NULL,
  `nombre_provincia` varchar(30) CHARACTER SET latin1 COLLATE latin1_general_ci NOT NULL,
  `idcomuna` varchar(10) CHARACTER SET latin1 COLLATE latin1_general_ci NOT NULL,
  `nombre_comuna` varchar(20) CHARACTER SET latin1 COLLATE latin1_general_ci NOT NULL,
  PRIMARY KEY (`idcomuna`),
  KEY `idregion` (`idregion`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `contratos_financieros`
--

DROP TABLE IF EXISTS `contratos_financieros`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `contratos_financieros` (
  `id_transaccion` bigint(20) NOT NULL AUTO_INCREMENT,
  `idversion` int(11) NOT NULL,
  `clave` varchar(255) NOT NULL,
  `id_hora_old` int(11) DEFAULT NULL,
  `energia_kwh` float DEFAULT NULL,
  `cmg_clp_kwh` float DEFAULT NULL,
  `valorizado_clp` float DEFAULT NULL,
  `rut_empresa` varchar(50) DEFAULT NULL,
  `id_barra` int(11) DEFAULT NULL,
  `transaccion` text DEFAULT NULL,
  `observacion` text DEFAULT NULL,
  `id_contrato` int(11) DEFAULT NULL,
  `id_hora` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id_transaccion`),
  KEY `FK_c_fin_med_hora_mensual` (`idversion`,`id_hora_old`),
  KEY `fk_contratos_hora` (`id_hora`),
  CONSTRAINT `fk_contratos_hora` FOREIGN KEY (`id_hora`) REFERENCES `hora_mensual` (`id_hora`)
) ENGINE=InnoDB AUTO_INCREMENT=9209954 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `contratos_fisicos`
--

DROP TABLE IF EXISTS `contratos_fisicos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `contratos_fisicos` (
  `idversion` int(11) NOT NULL,
  `id_contrato` int(11) DEFAULT NULL,
  `observacion` text DEFAULT NULL,
  `clave` varchar(255) NOT NULL,
  `rut_empresa` varchar(50) DEFAULT NULL,
  `id_barra` int(11) DEFAULT NULL,
  `transaccion` text DEFAULT NULL,
  `id_hora` bigint(20) DEFAULT NULL,
  `cmg_clp_kwh` float DEFAULT NULL,
  `energia_kwh` float DEFAULT NULL,
  `valorizado_clp` float DEFAULT NULL,
  `id_transaccion` bigint(20) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id_transaccion`),
  KEY `FK_c_fis_info_barra` (`id_barra`),
  KEY `FK_c_fis_info_empresa` (`rut_empresa`),
  KEY `idx_contratos_hora` (`id_hora`),
  CONSTRAINT `fk_contratos_empresa` FOREIGN KEY (`rut_empresa`) REFERENCES `empresa` (`rut_empresa`),
  CONSTRAINT `fk_contratos_hora_new` FOREIGN KEY (`id_hora`) REFERENCES `hora_mensual` (`id_hora`)
) ENGINE=InnoDB AUTO_INCREMENT=524281 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cv`
--

DROP TABLE IF EXISTS `cv`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `cv` (
  `idVersion` int(11) NOT NULL,
  `hora_mensual` int(11) NOT NULL,
  `id_hora` bigint(20) DEFAULT NULL,
  `idUnidadgen` int(11) NOT NULL,
  `cv_usd_mwh` float DEFAULT NULL,
  PRIMARY KEY (`idVersion`,`hora_mensual`,`idUnidadgen`) USING BTREE,
  KEY `idUnidadgen` (`idUnidadgen`),
  KEY `fk_cv_hora` (`id_hora`),
  CONSTRAINT `cv_ibfk_2` FOREIGN KEY (`idUnidadgen`) REFERENCES `unidad_generacion` (`id_unidad_generacion`),
  CONSTRAINT `fk_cv_hora` FOREIGN KEY (`id_hora`) REFERENCES `hora_mensual` (`id_hora`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `empresa`
--

DROP TABLE IF EXISTS `empresa`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `empresa` (
  `id_empresa` int(11) NOT NULL AUTO_INCREMENT,
  `rut_empresa` varchar(13) NOT NULL,
  `nombre` text DEFAULT NULL,
  PRIMARY KEY (`rut_empresa`),
  UNIQUE KEY `id_empresa` (`id_empresa`)
) ENGINE=InnoDB AUTO_INCREMENT=1047 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `gx_real`
--

DROP TABLE IF EXISTS `gx_real`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `gx_real` (
  `id_generacion` bigint(20) NOT NULL AUTO_INCREMENT,
  `id_central` int(11) NOT NULL,
  `nombre_unidadgen` varchar(255) DEFAULT NULL,
  `id_version` int(11) NOT NULL,
  `inyeccion_retiro` decimal(18,6) DEFAULT NULL,
  `id_hora` bigint(20) DEFAULT NULL,
  `subtipo` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id_generacion`),
  KEY `idx_gx_real_id_central` (`id_central`),
  KEY `fk_gxreal_horamensual` (`id_hora`),
  KEY `idx_gx_real_version_central` (`id_version`,`id_central`),
  KEY `idx_gx_real_version_unidad_gen` (`id_version`,`nombre_unidadgen`),
  KEY `idx_real_real_central_hora` (`id_central`,`id_hora`),
  CONSTRAINT `fk_gx_real_centrales_new` FOREIGN KEY (`id_central`) REFERENCES `central` (`id_central`),
  CONSTRAINT `fk_gxreal_horamensual` FOREIGN KEY (`id_hora`) REFERENCES `hora_mensual` (`id_hora`)
) ENGINE=InnoDB AUTO_INCREMENT=42348361 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Temporary table structure for view `gx_real_retiro`
--

DROP TABLE IF EXISTS `gx_real_retiro`;
/*!50001 DROP VIEW IF EXISTS `gx_real_retiro`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE VIEW `gx_real_retiro` AS SELECT
 1 AS `periodo_datos`,
  1 AS `fecha_hora`,
  1 AS `nombre_barra`,
  1 AS `tension`,
  1 AS `nombre_cmg`,
  1 AS `nombre_central`,
  1 AS `tipo_central`,
  1 AS `retiro` */;
SET character_set_client = @saved_cs_client;

--
-- Table structure for table `hora_mensual`
--

DROP TABLE IF EXISTS `hora_mensual`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `hora_mensual` (
  `id_hora` bigint(20) NOT NULL,
  `id_version` int(11) DEFAULT NULL,
  `cuarto_hora` int(11) DEFAULT NULL,
  `dia` int(11) DEFAULT NULL,
  `hora` int(11) DEFAULT NULL,
  `minuto` int(11) DEFAULT NULL,
  `fecha_hora` datetime DEFAULT NULL,
  `trimestre` tinyint(4) GENERATED ALWAYS AS (quarter(`fecha_hora`)) STORED,
  `dow` tinyint(4) GENERATED ALWAYS AS (dayofweek(`fecha_hora`)) STORED,
  `año` smallint(6) GENERATED ALWAYS AS (year(`fecha_hora`)) STORED,
  `mes` tinyint(4) GENERATED ALWAYS AS (month(`fecha_hora`)) STORED,
  PRIMARY KEY (`id_hora`),
  UNIQUE KEY `UNIQUE` (`id_version`,`dia`,`hora`,`minuto`) USING BTREE,
  KEY `hora` (`hora`),
  KEY `idx_hm_version_minuto` (`id_version`,`minuto`,`cuarto_hora`),
  KEY `idv_id_hora` (`id_version`,`cuarto_hora`,`hora`),
  KEY `idx_hora_mensual_fecha_hora` (`fecha_hora`),
  KEY `idx_hora_mensual_version_fecha` (`id_version`,`fecha_hora`),
  KEY `idx_hm_año_mes` (`año`,`mes`),
  KEY `idx_hm_version_año_mes` (`id_version`,`año`,`mes`),
  CONSTRAINT `fk_hora_version` FOREIGN KEY (`id_version`) REFERENCES `version` (`id_version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Temporary table structure for view `inyeccion_compensacion`
--

DROP TABLE IF EXISTS `inyeccion_compensacion`;
/*!50001 DROP VIEW IF EXISTS `inyeccion_compensacion`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE VIEW `inyeccion_compensacion` AS SELECT
 1 AS `id_version`,
  1 AS `nombre_empresa`,
  1 AS `cuarto_hora`,
  1 AS `precio_nudo`,
  1 AS `valorizado_pnudo`,
  1 AS `diferencia_pnudo_cmg`,
  1 AS `energia_sobre_9mwh`,
  1 AS `medida_15min_ajustada`,
  1 AS `prorrata_suministrador`,
  1 AS `diferencia_horaria` */;
SET character_set_client = @saved_cs_client;

--
-- Table structure for table `inyecciones`
--

DROP TABLE IF EXISTS `inyecciones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `inyecciones` (
  `id_version` int(11) NOT NULL,
  `clave` varchar(255) NOT NULL,
  `cuarto_hora` int(11) NOT NULL,
  `MedidaHoraria2` decimal(25,5) DEFAULT NULL,
  `MedidaHoraria` decimal(25,5) DEFAULT NULL,
  `CMG_PESO_KWH` decimal(20,5) DEFAULT NULL,
  `VALORIZADO_PESOS` decimal(20,5) DEFAULT NULL,
  `rut_empresa` varchar(13) DEFAULT NULL,
  `id_hora` bigint(20) DEFAULT NULL,
  `id_pe_inyeccion` int(11) DEFAULT NULL,
  `id_medidor` int(11) DEFAULT NULL,
  PRIMARY KEY (`id_version`,`clave`,`cuarto_hora`),
  KEY `FK_generacion_hora_mensual` (`id_version`,`cuarto_hora`),
  KEY `idx_idVersion` (`id_version`) USING BTREE,
  KEY `idversion_clave` (`id_version`,`clave`),
  KEY `idx_rut_empresa_iny` (`rut_empresa`),
  KEY `fk_inyecciones2_hora` (`id_hora`),
  KEY `fk_inyecciones2_pe` (`id_pe_inyeccion`),
  KEY `fk_inyecciones_medidor` (`id_medidor`),
  CONSTRAINT `fk_inyecciones2_empresa` FOREIGN KEY (`rut_empresa`) REFERENCES `empresa` (`rut_empresa`),
  CONSTRAINT `fk_inyecciones2_hora` FOREIGN KEY (`id_hora`) REFERENCES `hora_mensual` (`id_hora`),
  CONSTRAINT `fk_inyecciones2_pe` FOREIGN KEY (`id_pe_inyeccion`) REFERENCES `pe_inyecciones` (`id_pe_inyeccion`),
  CONSTRAINT `fk_inyecciones_medidor` FOREIGN KEY (`id_medidor`) REFERENCES `medidores` (`id_medidor`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `medidores`
--

DROP TABLE IF EXISTS `medidores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `medidores` (
  `id_medidor` int(11) NOT NULL AUTO_INCREMENT,
  `clave` varchar(255) NOT NULL,
  `id_barra` int(11) DEFAULT NULL,
  `nro_lt` decimal(18,5) DEFAULT NULL,
  `clave_lt` varchar(255) DEFAULT NULL,
  `idEmpresa` varchar(13) DEFAULT NULL,
  `tipo1` varchar(50) DEFAULT NULL,
  `zona` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id_medidor`),
  KEY `fk_medidor_barra` (`id_barra`),
  CONSTRAINT `fk_medidor_barra` FOREIGN KEY (`id_barra`) REFERENCES `barras` (`id_barra`)
) ENGINE=InnoDB AUTO_INCREMENT=65536 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pe_compensacion`
--

DROP TABLE IF EXISTS `pe_compensacion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `pe_compensacion` (
  `idVersion` int(11) NOT NULL,
  `hora_mensual` int(11) NOT NULL,
  `idEmpresa` varchar(13) NOT NULL DEFAULT '',
  `prorrata_suministrador` decimal(40,20) DEFAULT NULL,
  `diferencia_horaria` decimal(40,20) DEFAULT NULL,
  `compensacion` decimal(40,20) DEFAULT NULL,
  PRIMARY KEY (`idVersion`,`hora_mensual`,`idEmpresa`),
  KEY `FK_pe_compensacion_empresa_` (`idEmpresa`),
  CONSTRAINT `FK_pe_compensacion_empresa_` FOREIGN KEY (`idEmpresa`) REFERENCES `empresa` (`rut_empresa`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `pe_compensacion_ibfk_1` FOREIGN KEY (`idVersion`) REFERENCES `version` (`id_version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pe_inyecciones`
--

DROP TABLE IF EXISTS `pe_inyecciones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `pe_inyecciones` (
  `id_version` int(11) DEFAULT NULL,
  `clave` varchar(255) NOT NULL,
  `cuarto_hora` int(11) NOT NULL,
  `precio_nudo` decimal(40,20) DEFAULT NULL,
  `valorizado_pnudo` decimal(40,20) DEFAULT NULL,
  `diferencia_pnudo_cmg` decimal(40,20) DEFAULT NULL,
  `energia_sobre_9mwh` decimal(40,20) DEFAULT 0.00000000000000000000,
  `medida_15min_ajustada` decimal(40,20) DEFAULT 0.00000000000000000000,
  `observacion` text DEFAULT '',
  `id_pe_inyeccion` int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id_pe_inyeccion`)
) ENGINE=InnoDB AUTO_INCREMENT=35649592 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Temporary table structure for view `proporcion_renovables`
--

DROP TABLE IF EXISTS `proporcion_renovables`;
/*!50001 DROP VIEW IF EXISTS `proporcion_renovables`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE VIEW `proporcion_renovables` AS SELECT
 1 AS `año`,
  1 AS `mes`,
  1 AS `tipo_tecnologia`,
  1 AS `subtipo`,
  1 AS `total_inyeccion`,
  1 AS `total_sistema`,
  1 AS `proporcion_renovable` */;
SET character_set_client = @saved_cs_client;

--
-- Table structure for table `retiro`
--

DROP TABLE IF EXISTS `retiro`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `retiro` (
  `id_version` int(11) NOT NULL,
  `clave` varchar(255) NOT NULL,
  `cuarto_hora` int(11) NOT NULL,
  `MedidaHoraria2` decimal(25,5) DEFAULT NULL,
  `MedidaHoraria` decimal(25,5) DEFAULT NULL,
  `CMG_PESO_KWH` decimal(20,5) DEFAULT NULL,
  `VALORIZADO_PESOS` decimal(20,5) DEFAULT NULL,
  `id_medidor` int(11) DEFAULT NULL,
  `id_hora` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id_version`,`clave`,`cuarto_hora`),
  KEY `k1` (`id_version`,`clave`),
  KEY `k2` (`id_version`,`cuarto_hora`),
  KEY `Índice 4` (`id_version`),
  KEY `fk_retiro_medidor` (`id_medidor`),
  KEY `fk_retiro_hora` (`id_hora`),
  CONSTRAINT `fk_retiro_hora` FOREIGN KEY (`id_hora`) REFERENCES `hora_mensual` (`id_hora`),
  CONSTRAINT `fk_retiro_medidor` FOREIGN KEY (`id_medidor`) REFERENCES `medidores` (`id_medidor`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `retiro_regulado`
--

DROP TABLE IF EXISTS `retiro_regulado`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `retiro_regulado` (
  `id_retiro_regulado` int(11) NOT NULL AUTO_INCREMENT,
  `id_version` int(11) NOT NULL,
  `bloque_regulado` varchar(10) DEFAULT NULL,
  `idempresa_br` int(11) NOT NULL,
  `idempresa_sum` int(11) NOT NULL,
  `kwh_ps1` float DEFAULT NULL,
  `%_ps1` float DEFAULT NULL,
  `kwh_ps2` float DEFAULT NULL,
  `%_ps2` float DEFAULT NULL,
  `fisico_kwh` float DEFAULT NULL,
  `monetario` float DEFAULT NULL,
  PRIMARY KEY (`id_retiro_regulado`),
  KEY `FK_retiro_regulado_empresa_` (`idempresa_br`),
  KEY `FK_retiro_regulado_empresa__2` (`idempresa_sum`),
  CONSTRAINT `fk_retiro_regulado_br` FOREIGN KEY (`idempresa_br`) REFERENCES `empresa` (`id_empresa`),
  CONSTRAINT `fk_retiro_regulado_sum` FOREIGN KEY (`idempresa_sum`) REFERENCES `empresa` (`id_empresa`),
  CONSTRAINT `retiro_regulado_ibfk_1` FOREIGN KEY (`id_version`) REFERENCES `version` (`id_version`)
) ENGINE=InnoDB AUTO_INCREMENT=131071 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sobrecostos`
--

DROP TABLE IF EXISTS `sobrecostos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sobrecostos` (
  `idVersion` int(11) NOT NULL,
  `hora_mensual` int(11) NOT NULL,
  `id_hora` bigint(20) DEFAULT NULL,
  `idUnidadgen` int(11) NOT NULL,
  `tipo` text DEFAULT NULL,
  `sobrecosto_clp` float DEFAULT NULL,
  `zona_pago` text DEFAULT NULL,
  `gen` float DEFAULT NULL,
  `cons_propio` float DEFAULT NULL,
  `cv` float DEFAULT NULL,
  `cmg` float DEFAULT NULL,
  `sscc` text DEFAULT NULL,
  PRIMARY KEY (`idVersion`,`hora_mensual`,`idUnidadgen`),
  KEY `idUnidadgen` (`idUnidadgen`),
  KEY `fk_sobrecostos_hora` (`id_hora`),
  CONSTRAINT `fk_sobrecostos_hora` FOREIGN KEY (`id_hora`) REFERENCES `hora_mensual` (`id_hora`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `sobrecostos_ibfk_2` FOREIGN KEY (`idUnidadgen`) REFERENCES `unidad_generacion` (`id_unidad_generacion`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Temporary table structure for view `sscc`
--

DROP TABLE IF EXISTS `sscc`;
/*!50001 DROP VIEW IF EXISTS `sscc`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE VIEW `sscc` AS SELECT
 1 AS `periodo_datos`,
  1 AS `nombre_empresa`,
  1 AS `rut_empresa`,
  1 AS `remuneracion_infra`,
  1 AS `recaudacion_infra`,
  1 AS `neto_infra`,
  1 AS `concepto`,
  1 AS `recibe_RT`,
  1 AS `paga_RT`,
  1 AS `sen_RT`,
  1 AS `total_neto_sen` */;
SET character_set_client = @saved_cs_client;

--
-- Table structure for table `sscc_infra`
--

DROP TABLE IF EXISTS `sscc_infra`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sscc_infra` (
  `idVersion` int(11) NOT NULL,
  `idEmpresa` varchar(13) NOT NULL DEFAULT '',
  `remuneracion` float DEFAULT NULL,
  `recaudacion` float DEFAULT NULL,
  `neto` float DEFAULT NULL,
  PRIMARY KEY (`idVersion`,`idEmpresa`),
  KEY `FK_sscc_infra_empresa_` (`idEmpresa`),
  CONSTRAINT `FK_sscc_infra_empresa_` FOREIGN KEY (`idEmpresa`) REFERENCES `empresa` (`rut_empresa`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `sscc_infra_ibfk_1` FOREIGN KEY (`idVersion`) REFERENCES `version` (`id_version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sscc_rt`
--

DROP TABLE IF EXISTS `sscc_rt`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sscc_rt` (
  `idVersion` int(11) NOT NULL,
  `concepto` text NOT NULL,
  `idEmpresa` varchar(13) NOT NULL DEFAULT '',
  `recibe` float DEFAULT NULL,
  `paga` float DEFAULT NULL,
  `sen` float DEFAULT NULL,
  PRIMARY KEY (`idVersion`,`concepto`(100),`idEmpresa`) USING BTREE,
  KEY `FK_sscc_rt_empresa_` (`idEmpresa`),
  CONSTRAINT `FK_sscc_rt_empresa_` FOREIGN KEY (`idEmpresa`) REFERENCES `empresa` (`rut_empresa`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `sscc_rt_ibfk_1` FOREIGN KEY (`idVersion`) REFERENCES `version` (`id_version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `subestacion`
--

DROP TABLE IF EXISTS `subestacion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `subestacion` (
  `id_subestacion` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) CHARACTER SET latin1 COLLATE latin1_general_ci NOT NULL,
  `idregion` varchar(10) CHARACTER SET latin1 COLLATE latin1_general_ci NOT NULL,
  `idprovincia` varchar(10) CHARACTER SET latin1 COLLATE latin1_general_ci NOT NULL,
  `idcomuna` varchar(10) CHARACTER SET latin1 COLLATE latin1_general_ci NOT NULL,
  `tipoconfiguracion` varchar(50) CHARACTER SET latin1 COLLATE latin1_general_ci DEFAULT NULL,
  `entrada_en_operaci_n` varchar(10) CHARACTER SET latin1 COLLATE latin1_general_ci DEFAULT NULL,
  `coordenada_este` varchar(20) CHARACTER SET latin1 COLLATE latin1_general_ci DEFAULT NULL,
  `coordenada_norte` varchar(20) CHARACTER SET latin1 COLLATE latin1_general_ci DEFAULT NULL,
  `huso` varchar(10) CHARACTER SET latin1 COLLATE latin1_general_ci DEFAULT NULL,
  `observacion` varchar(30) CHARACTER SET latin1 COLLATE latin1_general_ci DEFAULT NULL,
  PRIMARY KEY (`id_subestacion`),
  KEY `FK_subestacion_codigoterritorio` (`idcomuna`),
  CONSTRAINT `FK_subestacion_codigoterritorio` FOREIGN KEY (`idcomuna`) REFERENCES `codigo_territorio` (`idcomuna`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=24367 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `transmision`
--

DROP TABLE IF EXISTS `transmision`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `transmision` (
  `id_version` int(11) NOT NULL,
  `clave` varchar(255) NOT NULL,
  `cuarto_hora` int(11) NOT NULL,
  `MedidaHoraria2` decimal(25,5) DEFAULT NULL,
  `MedidaHoraria` decimal(25,5) DEFAULT NULL,
  `CMG_PESO_KWH` decimal(20,5) DEFAULT NULL,
  `VALORIZADO_PESOS` decimal(20,5) DEFAULT NULL,
  `id_hora` bigint(20) DEFAULT NULL,
  `id_medidor` int(11) DEFAULT NULL,
  PRIMARY KEY (`id_version`,`clave`,`cuarto_hora`),
  KEY `fk_transmision_new_hora` (`id_hora`),
  KEY `fk_transmision_new_medidor` (`id_medidor`),
  CONSTRAINT `fk_transmision_new_hora` FOREIGN KEY (`id_hora`) REFERENCES `hora_mensual` (`id_hora`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_transmision_new_medidor` FOREIGN KEY (`id_medidor`) REFERENCES `medidores` (`id_medidor`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `unidad_generacion`
--

DROP TABLE IF EXISTS `unidad_generacion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `unidad_generacion` (
  `id_unidad_generacion` int(11) NOT NULL,
  `Nombre` varchar(255) CHARACTER SET latin1 COLLATE latin1_general_ci DEFAULT NULL,
  `id_central` int(11) DEFAULT NULL,
  `Combustible` varchar(255) CHARACTER SET latin1 COLLATE latin1_general_ci DEFAULT NULL,
  PRIMARY KEY (`id_unidad_generacion`),
  KEY `Nombre` (`Nombre`),
  KEY `fk_unidad_central` (`id_central`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `version`
--

DROP TABLE IF EXISTS `version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `version` (
  `id_version` int(11) NOT NULL,
  `periodo` date DEFAULT NULL,
  `tipo` varchar(255) DEFAULT NULL,
  `nombre` varchar(255) DEFAULT NULL,
  `año` int(11) GENERATED ALWAYS AS (year(`periodo`)) STORED,
  `mes` int(11) GENERATED ALWAYS AS (month(`periodo`)) STORED,
  PRIMARY KEY (`id_version`),
  UNIQUE KEY `uk_version` (`periodo`,`tipo`),
  KEY `periodo` (`periodo`) USING BTREE,
  KEY `idx_anio` (`año`),
  KEY `idx_mes` (`mes`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `vertimiento`
--

DROP TABLE IF EXISTS `vertimiento`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `vertimiento` (
  `id_vertimiento` bigint(20) NOT NULL AUTO_INCREMENT,
  `id_version` int(11) NOT NULL,
  `id_central` int(11) DEFAULT NULL,
  `id_unidadgen` int(11) DEFAULT NULL,
  `id_hora` bigint(20) DEFAULT NULL,
  `tipo` text NOT NULL,
  `nombre_unidadgen` varchar(255) DEFAULT NULL,
  `vertimiento` float DEFAULT NULL,
  PRIMARY KEY (`id_vertimiento`),
  KEY `idx_id_version` (`id_version`),
  KEY `idx_id_central` (`id_central`),
  KEY `idx_id_hora` (`id_hora`),
  CONSTRAINT `fk_central` FOREIGN KEY (`id_central`) REFERENCES `central` (`id_central`),
  CONSTRAINT `fk_hora` FOREIGN KEY (`id_hora`) REFERENCES `hora_mensual` (`id_hora`)
) ENGINE=InnoDB AUTO_INCREMENT=6378283 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Final view structure for view `cmg_barra`
--

/*!50001 DROP VIEW IF EXISTS `cmg_barra`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `cmg_barra` AS select `v`.`nombre` AS `periodo_datos`,`hm`.`fecha_hora` AS `fecha_hora`,`b`.`nombre` AS `nombre_barra`,`b`.`tension` AS `tension`,`b`.`nombre_cmg` AS `nombre_cmg`,`c`.`CMG_PESO_KWH` AS `CMG_PESO_KWH`,`c`.`CMG_DOLAR_MWH` AS `CMG_DOLAR_MWH` from (((`cmg` `c` join `version` `v` on(`c`.`id_version` = `v`.`id_version`)) join `hora_mensual` `hm` on(`c`.`id_version` = `hm`.`id_version` and `c`.`id_hora` = `hm`.`id_hora`)) join `barras` `b` on(`c`.`id_barra` = `b`.`id_barra`)) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `gx_real_retiro`
--

/*!50001 DROP VIEW IF EXISTS `gx_real_retiro`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `gx_real_retiro` AS select `v`.`nombre` AS `periodo_datos`,`h`.`fecha_hora` AS `fecha_hora`,`b`.`nombre` AS `nombre_barra`,`b`.`tension` AS `tension`,`b`.`nombre_cmg` AS `nombre_cmg`,`c`.`nombre_central` AS `nombre_central`,`c`.`tipo` AS `tipo_central`,`g`.`inyeccion_retiro` AS `retiro` from (((((`gx_real` `g` join `hora_mensual` `h` on(`g`.`id_hora` = `h`.`id_hora`)) join `central` `c` on(`g`.`id_central` = `c`.`id_central`)) join `version` `v` on(`g`.`id_version` = `v`.`id_version`)) join `subestacion` `s` on(`c`.`id_subestacion` = `s`.`id_subestacion`)) join `barras` `b` on(`s`.`id_subestacion` = `b`.`id_subestacion`)) where `g`.`inyeccion_retiro` < 0 */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `inyeccion_compensacion`
--

/*!50001 DROP VIEW IF EXISTS `inyeccion_compensacion`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `inyeccion_compensacion` AS select `v`.`id_version` AS `id_version`,`e`.`nombre` AS `nombre_empresa`,`p`.`cuarto_hora` AS `cuarto_hora`,`p`.`precio_nudo` AS `precio_nudo`,`p`.`valorizado_pnudo` AS `valorizado_pnudo`,`p`.`diferencia_pnudo_cmg` AS `diferencia_pnudo_cmg`,`p`.`energia_sobre_9mwh` AS `energia_sobre_9mwh`,`p`.`medida_15min_ajustada` AS `medida_15min_ajustada`,`pc`.`prorrata_suministrador` AS `prorrata_suministrador`,`pc`.`diferencia_horaria` AS `diferencia_horaria` from ((((`pe_inyecciones` `p` join `version` `v` on(`p`.`id_version` = `v`.`id_version`)) join `medidores` `m` on(`p`.`clave` = `m`.`clave`)) join `empresa` `e` on(`m`.`idEmpresa` = `e`.`rut_empresa`)) join `pe_compensacion` `pc` on(`p`.`id_version` = `pc`.`idVersion` and `p`.`cuarto_hora` = `pc`.`hora_mensual` and `e`.`rut_empresa` = `pc`.`idEmpresa`)) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `proporcion_renovables`
--

/*!50001 DROP VIEW IF EXISTS `proporcion_renovables`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`pinzunza`@`%` SQL SECURITY DEFINER */
/*!50001 VIEW `proporcion_renovables` AS with renovables as (select `hor`.`año` AS `año`,`hor`.`mes` AS `mes`,`cen`.`tipo` AS `tipo_tecnologia`,`gx`.`subtipo` AS `subtipo`,sum(`gx`.`inyeccion_retiro`) AS `total_inyeccion` from ((`gx_real` `gx` join `central` `cen` on(`gx`.`id_central` = `cen`.`id_central`)) join `hora_mensual` `hor` on(`gx`.`id_hora` = `hor`.`id_hora`)) where `cen`.`tipo` in ('Hidroeléctricas','Geotérmica','Solar','Eólicas','Mareomotriz') or `cen`.`tipo` = 'Termoeléctricas' and `gx`.`subtipo` in ('Biomasa','BioGas') group by `hor`.`año`,`hor`.`mes`,`cen`.`tipo`,`gx`.`subtipo`), total_sistema as (select `hor`.`año` AS `año`,`hor`.`mes` AS `mes`,sum(`gx`.`inyeccion_retiro`) AS `total_inyeccion` from (`gx_real` `gx` join `hora_mensual` `hor` on(`gx`.`id_hora` = `hor`.`id_hora`)) group by `hor`.`año`,`hor`.`mes`)select `r`.`año` AS `año`,`r`.`mes` AS `mes`,`r`.`tipo_tecnologia` AS `tipo_tecnologia`,`r`.`subtipo` AS `subtipo`,`r`.`total_inyeccion` AS `total_inyeccion`,`t`.`total_inyeccion` AS `total_sistema`,round(`r`.`total_inyeccion` / `t`.`total_inyeccion` * 100,2) AS `proporcion_renovable` from (`renovables` `r` join `total_sistema` `t` on(`r`.`año` = `t`.`año` and `r`.`mes` = `t`.`mes`)) order by `r`.`año`,`r`.`mes`,`r`.`tipo_tecnologia`,`r`.`subtipo` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `sscc`
--

/*!50001 DROP VIEW IF EXISTS `sscc`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `sscc` AS select `v`.`nombre` AS `periodo_datos`,`e`.`nombre` AS `nombre_empresa`,`e`.`rut_empresa` AS `rut_empresa`,`si`.`remuneracion` AS `remuneracion_infra`,`si`.`recaudacion` AS `recaudacion_infra`,`si`.`neto` AS `neto_infra`,`sr`.`concepto` AS `concepto`,`sr`.`recibe` AS `recibe_RT`,`sr`.`paga` AS `paga_RT`,`sr`.`sen` AS `sen_RT`,`sr`.`sen` + `si`.`neto` AS `total_neto_sen` from (((`sscc_infra` `si` join `version` `v` on(`si`.`idVersion` = `v`.`id_version`)) join `empresa` `e` on(`si`.`idEmpresa` = `e`.`rut_empresa`)) join `sscc_rt` `sr` on(`si`.`idVersion` = `sr`.`idVersion` and `si`.`idEmpresa` = `sr`.`idEmpresa`)) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-04-08 17:05:42
