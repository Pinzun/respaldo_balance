import pandas as pd
import numpy as np

#Leer datos desde archivo de barras de balance
ruta_balance = r"C:\Users\reportes\data_projects\actualizacion_bd_balance\data\raw\energia\2025\2510\Barras_export_1763737325069.xlsx"
barras_balance = pd.read_excel(ruta_balance, sheet_name="data", dtype=str)

#Leer datos desde archivo de barras infotecnica
ruta_infotecnica = r"C:\Users\reportes\data_projects\actualizacion_bd_balance\reporte_barras.xlsx"
barras_infotecnica = pd.read_excel(ruta_infotecnica, sheet_name="Informacion Barras", dtype=str, header=6)

#Conservar solo columnas útiles desde infotecnica

barras_infotecnica = barras_infotecnica[[
    'ID',
    'Nombre',
    'Nombre Subestación',
    '18.6 Fecha de entrada en operación'
]]


print("Datos de barras_infotecnica:")
print(barras_infotecnica.head(5))
print("Datos de barras_balance:")   
print(barras_balance.head(5))


barras_balance = barras_balance.rename(columns={
    'Empresa Propietaria': 'Empresa'
})
#Merge entre ambos dataframes
barras_merged = pd.merge(
    barras_balance[['Barra', 'Nivel de tensión', 'Barra infotécnica', 'Código barra CNE', 'Nombre barra CNE', 'Subestación', 'Comuna', 'Calificación', 'Zona concesión', 'Empresa', 'Zona Transmisión']],
    barras_infotecnica[['ID', '18.6 Fecha de entrada en operación']],
    left_on="Barra infotécnica",
    right_on="ID",
    how="left"
)

barras_merged = barras_merged.rename(columns={
    '18.6 Fecha de entrada en operación': 'entrada_operacion'
})
barras_merged = barras_merged.drop(columns=['ID'])


print("Datos de barras_merged:")
print(barras_merged.head(5))

barras_merged.to_csv(r"C:\Users\reportes\data_projects\actualizacion_bd_balance\barras_transicion.csv", index=False, encoding="utf-8")