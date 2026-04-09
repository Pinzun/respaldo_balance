-- Las siguientes instrucciones, crean la base de datos importar_balance, la que corresponde a una base intermedia 
-- utilizada para cargar la información procesada por los scripts de actualización
DROP DATABASE importar;
-- Corregimos character set de balance, más adelante hay que corregir para todas las tablas
ALTER DATABASE balance
CHARACTER SET utf8mb4
COLLATE utf8mb4_general_ci;
-- revisamos collation y character set de la tabla madre
SHOW CREATE DATABASE balance;
-- Creamos importar balance con el mismo collation y character set
CREATE DATABASE IF NOT EXISTS importar_balance
DEFAULT CHARACTER SET utf8mb4
COLLATE utf8mb4_general_ci;
