# -*- coding: utf-8 -*-
import os
import re
import unicodedata
from pathlib import Path

import pandas as pd
from pandas import NA
from rapidfuzz import process, fuzz

from ...db.db_utils import open_connection, close_connection


# =========================
# RUTAS / ARCHIVOS
# =========================
DIR_BASE = Path(__file__).parent.parent
DATA_RAW = DIR_BASE / "data" / "raw"
DATA_PROCESSED = DIR_BASE / "data" / "processed"

DATA_CENTRALES = DATA_RAW / "reporte_centrales.xlsx"
DATA_SUBESTACIONES = DATA_PROCESSED / "subestaciones_bd.xlsx"

OUT_FULL = DATA_PROCESSED / "gx_real_full.csv"
OUT_CENTRALES = DATA_PROCESSED / "centrales.csv"
OUT_GX_REAL = DATA_PROCESSED / "gx_real"/ "gx_real.csv"


# =========================
# DICCIONARIO DE VERSIONES
# =========================
id_version_dict = {
    "2022-12-01": 1, "2022-11-01": 2, "2022-10-01": 3, "2022-09-01": 4,
    "2022-08-01": 5, "2022-07-01": 6, "2022-06-01": 7, "2022-05-01": 8,
    "2022-03-01": 10, "2022-02-01": 11, "2022-01-01": 12, "2022-04-01": 15,
    "2023-01-01": 16, "2023-02-01": 17, "2023-03-01": 19, "2023-04-01": 20,
    "2023-05-01": 21, "2023-06-01": 22, "2023-07-01": 25, "2023-08-01": 26,
    "2023-09-01": 27, "2023-10-01": 28, "2023-11-01": 29, "2023-12-01": 30,
    "2024-01-01": 31, "2024-02-01": 32, "2024-03-01": 33, "2024-04-01": 34,
    "2024-05-01": 35, "2024-06-01": 36, "2024-07-01": 38, "2024-08-01": 39,
    "2024-09-01": 40, "2024-10-01": 41, "2025-04-01": 42, "2024-11-01": 43,
    "2024-12-01": 44, "2025-01-01": 45, "2025-03-01": 46, "2025-02-01": 47,
    "2025-05-01": 48, "2025-06-01": 49, "2025-07-01": 50, "2025-08-01": 51,
    "2025-09-01": 52, "2025-10-01": 53, "2025-11-01": 54, "2025-12-01": 55,
    "2026-01-01": 56, "2026-02-01": 57, "2026-03-01": 58
}
clean_dict = {k[:7]: v for k, v in id_version_dict.items()}


# =========================
# CORRECCIONES MANUALES
# =========================
dict_remplazo_central = {
    "BESS La Cabaña": "S/E LA CABAÑA",
    "BESS ALFALFAL VR1": "S/E CENTRAL ALFALFAL",
    "BESS ALFALFAL VR2": "S/E CENTRAL ALFALFAL",
    "BESS Andes": "S/E ANDES (AES ANDES)",
    "BESS Andes IV": "S/E ANDES (AES ANDES)",
    "BESS Andes Solar IIA": "S/E ANDES SOLAR II",
    "BESS Andes Solar IIB": "S/E ANDES SOLAR II",
    "BESS Andes Solar III": "S/E FUTURO",
    "BESS Angamos": "S/E ANGAMOS",
    "BESS Arena": "S/E COCHRANE",
    "BESS Arenales": "S/E COCHRANE",
    "BESS Arica": "S/E ARICA",
    "BESS Bolero": "S/E LABERINTO",
    "BESS Capricornio": "S/E ELEVADORA CAPRICORNIO",
    "BESS Cochrane": "S/E GIS COCHRANE BESS",
    "BESS Desierto de Atacama": "S/E SOL DEL DESIERTO",
    "BESS Diego de Almagro Sur": "S/E INCA DE ORO",
    "BESS Don Humberto": "S/E DON HUMBERTO",
    "BESS Fragata": "S/E CASAS VIEJAS",
    "BESS Huatacondo": "S/E SANTA RITA",
    "BESS Manzano": "S/E EL MANZANO (CGE)",
    "BESS María Elena": "S/E MARIA ELENA",
    "BESS Nueva Imperial": "S/E IMPERIAL",
    "BESS Nuevo Quillagua": "S/E PEQ",
    "BESS Nuevo Quillagua II": "S/E PEQ",
    "BESS PFV COYA": "S/E PALPANA",
    "BESS Punta Sierra": "S/E PUNTA SIERRA",
    "BESS Rita del Maitén": "S/E PUENTE ALTO (TEC)",
    "BESS Salvador": "S/E CENTRAL PV SALVADOR",
    "BESS San Andrés": "S/E CENTRAL SAN ANDRES (SAN ANDRES SPA)",
    "BESS Tamaya": "S/E CENTRAL DIESEL TAMAYA",
    "BESS Tocopilla": "S/E CENTRAL TOCOPILLA",
    "BESS Uribe Solar": "S/E URIBE SOLAR",
    "BESS del Desierto": "S/E SOL DEL DESIERTO",
    "HP ALFALFAL II": "S/E CENTRAL ALFALFAL",
    "PE LOS OLMOS": "S/E LOS OLMOS",
    "PFV DE LOS ANDES": "S/E ANDES (AES ANDES)",
    "PFV DEL DESIERTO": "S/E ANDES (AES ANDES)",
    "PFV MACHICURA": "S/E PFV MACHICURA",
    "PFV SOL DE LILA": "S/E ANDES (AES ANDES)",
    "PFV VENEZIA SOLAR": "S/E TENO",
    "TER SAN JAVIER I": "S/E CENTRAL SAN JAVIER",
    "TER SAN JAVIER II": "S/E CENTRAL SAN JAVIER",
    "TER SAN LORENZO DE D. DE ALMAGRO": "S/E CENTRAL SAN LORENZO DE DIEGO DE ALMAGRO",
}


# =========================
# HELPERS
# =========================
def extrae_data_subestacion() -> pd.DataFrame:
    conn, ssh_client, stop_event = open_connection()
    q = "SELECT * FROM balance.subestacion;"
    with conn.cursor() as cursor:
        cursor.execute(q)
        data = cursor.fetchall()
    close_connection(conn, ssh_client, stop_event)
    return pd.DataFrame(data)


def load_csv_files(directory: Path) -> pd.DataFrame:
    csv_files = list(directory.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No se encontraron archivos .csv en {directory}")
    dfs = [pd.read_csv(f, sep=";") for f in csv_files]
    return pd.concat(dfs, ignore_index=True)


def transformar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Asegurar fecha real
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["Fecha_ym"] = df["Fecha"].dt.strftime("%Y-%m")
    df["id_version"] = df["Fecha_ym"].map(clean_dict).astype("Int64")

    columnas_fijas = [
        "Central",
        "Coordinado",
        "Llave",
        "Grupo reporte",
        "Tipo",
        "Subtipo",
        "Fecha",
        "Fecha_ym",
        "id_version",
    ]
    columnas_fijas = [c for c in columnas_fijas if c in df.columns]

    columnas_horas = [c for c in df.columns if str(c).strip().lower().startswith("hora")]
    if not columnas_horas:
        raise ValueError("No se encontraron columnas de horas (ej: 'Hora 1', 'Hora_1', 'Hora1').")

    df_long = df.melt(
        id_vars=columnas_fijas,
        value_vars=columnas_horas,
        var_name="hora",
        value_name="inyeccion_retiro",
    )

    df_long["hora"] = (
        df_long["hora"]
        .astype(str)
        .str.extract(r"(\d+)", expand=False)
        .astype("Int64")
    )

    df_long["fecha_hora"] = (
        pd.to_datetime(df_long["Fecha"], errors="coerce")
        + pd.to_timedelta(df_long["hora"] - 1, unit="h")
    ).dt.strftime("%Y-%m-%d %H:%M:%S")

    if "Central" in df_long.columns:
        df_long["Central"] = (
            df_long["Central"]
            .astype(str)
            .str.replace(r"\[NO_MOSTRAR\]", "", regex=True)
            .str.replace(r"\[EN_REVISION\]", "", regex=True)
            .str.replace(r"\[En_Revision\]", "", regex=True)
            .str.replace(r"\[No_Mostrar\]", "", regex=True)
            .str.strip()
        )

    df_long.columns = (
        df_long.columns
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    df_long.rename(columns={"llave": "nombre_unidadgen"}, inplace=True)

    return df_long

def transformar_centrales(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "Nombre",
        "Nombre Coordinado",
        "ID",
        "11.1.2 Puntos de conexión al SI a través de los cuales inyecta energía.",
    ]
    df_c = df[cols].copy()
    df_c = df_c.rename(columns={
        "11.1.2 Puntos de conexión al SI a través de los cuales inyecta energía.": "punto_conexion_sen"
    })
    df_c.columns = df_c.columns.str.lower().str.replace(" ", "_")
    return df_c


def limpia_punto_conexion(df: pd.DataFrame) -> pd.DataFrame:
    s = df["punto_conexion_sen"].astype("string")
    df["punto_conexion_sen_limpio"] = (
        s
        .str.replace(r"[\r\n\t]+", " ", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .str.replace(r"^[\s\S]*?(S\/E)", r"\1", regex=True)
        .str.replace(r"\b\d+\s*kV\b(?:\s*\w+)?", "", regex=True, flags=re.IGNORECASE)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    return df


def normalize_upper_no_accents_keep_enye(s: pd.Series) -> pd.Series:
    s = s.astype("string")

    s = s.str.replace("Ñ", "__ENYE_MAY__", regex=False)
    s = s.str.replace("ñ", "__ENYE_MIN__", regex=False)

    s = s.apply(lambda x: unicodedata.normalize("NFKD", x) if x is not pd.NA else x)
    s = s.apply(lambda x: "".join(ch for ch in x if not unicodedata.combining(ch)) if x is not pd.NA else x)

    s = s.str.replace("__ENYE_MAY__", "Ñ", regex=False)
    s = s.str.replace("__ENYE_MIN__", "Ñ", regex=False)

    s = (
        s.str.replace(r"[\r\n\t]+", " ", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .str.upper()
    )
    return s


def fuzzy_fill_id_subestacion_inplace(
    gx: pd.DataFrame,
    subest: pd.DataFrame,
    left_col="punto_conexion_sen_limpio",
    right_col="nombre",
    id_col="id_subestacion",
    threshold=90,
    scorer=fuzz.token_set_ratio,
    save_audit_xlsx=None,
) -> None:
    sub_map = (
        subest[[right_col, id_col]]
        .dropna(subset=[right_col, id_col])
        .drop_duplicates(subset=[right_col])
        .set_index(right_col)[id_col]
        .to_dict()
    )
    choices = list(sub_map.keys())

    mask = gx[id_col].isna() & gx[left_col].notna()
    queries = gx.loc[mask, left_col].drop_duplicates().tolist()

    rows = []
    q_to_id = {}

    for q in queries:
        best = process.extractOne(q, choices, scorer=scorer)
        if not best:
            continue
        match_name, score, _ = best
        if score >= threshold:
            mid = sub_map.get(match_name)
            q_to_id[q] = mid
            rows.append((q, match_name, score, mid))

    if rows and save_audit_xlsx:
        pd.DataFrame(rows, columns=[left_col, "match_nombre", "score", id_col]) \
            .sort_values(["score", left_col], ascending=[False, True]) \
            .to_excel(save_audit_xlsx, index=False)

    if q_to_id:
        gx.loc[mask, id_col] = gx.loc[mask, left_col].map(q_to_id).astype("Int64")


def build_id_central_no_merge(gx_out: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    key_cols = ["nombre_central", "grupo_reporte", "tipo", "subtipo", "coordinado"]

    for c in key_cols:
        if c not in gx_out.columns:
            gx_out[c] = NA

    key_df = gx_out[key_cols].fillna("").astype("string")

    key_hash = pd.util.hash_pandas_object(key_df, index=False).astype("uint64")
    gx_out["_key_hash"] = key_hash

    centrales_cols = [
        "nombre_central",
        "id_infotecnica",
        "coordinado",
        "grupo_reporte",
        "tipo",
        "subtipo",
        "punto_conexion_sen",
        "punto_conexion_sen_limpio",
        "id_subestacion",
        "tecnologia",
        "id_empresa",
        "observacion",
        "_key_hash",
    ]
    for c in centrales_cols:
        if c not in gx_out.columns:
            gx_out[c] = NA

    centrales_df = (
        gx_out[centrales_cols]
        .drop_duplicates(subset=["_key_hash"])
        .sort_values("_key_hash")
        .reset_index(drop=True)
    )

    centrales_df.insert(0, "id_central", pd.RangeIndex(start=1, stop=len(centrales_df) + 1, step=1))

    hash_to_id = pd.Series(
        centrales_df["id_central"].values,
        index=centrales_df["_key_hash"]
    ).to_dict()

    id_central_series = gx_out["_key_hash"].map(hash_to_id).astype("Int64")
    return centrales_df, id_central_series


# =========================
# MAIN
# =========================
def main():   
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    OUT_GX_REAL.parent.mkdir(parents=True, exist_ok=True)

    # 1) Cargar GX real + reporte centrales
    gx_raw = load_csv_files(DATA_RAW)
    centrales_xlsx = pd.read_excel(DATA_CENTRALES, skiprows=6)

    # 2) Subestaciones cache
    if not os.path.exists(DATA_SUBESTACIONES):
        subest = extrae_data_subestacion()
        subest.to_excel(DATA_SUBESTACIONES, index=False)
    else:
        subest = pd.read_excel(DATA_SUBESTACIONES)

    # Mojibake Ñ
    if "nombre" in subest.columns:
        subest["nombre"] = (
            subest["nombre"]
            .astype("string")
            .str.replace("Ã±", "Ñ", regex=False)
            .str.replace("Ã‘", "Ñ", regex=False)
        )

    # 3) Transformaciones
    gx = transformar(gx_raw)
    cent = transformar_centrales(centrales_xlsx)

    # 4) Merge “chico” con reporte centrales
    gx_out = gx.merge(cent, how="left", left_on="central", right_on="nombre")

    # 5) Limpieza punto conexión
    gx_out = limpia_punto_conexion(gx_out)

    # 6) Normalizaciones
    gx_out["punto_conexion_sen_limpio"] = normalize_upper_no_accents_keep_enye(gx_out["punto_conexion_sen_limpio"])
    subest["nombre"] = normalize_upper_no_accents_keep_enye(subest["nombre"])

    # 7) Match exacto id_subestacion vía map
    sub_map_exact = (
        subest[["nombre", "id_subestacion"]]
        .dropna()
        .drop_duplicates(subset=["nombre"])
        .set_index("nombre")["id_subestacion"]
        .to_dict()
    )
    gx_out["id_subestacion"] = gx_out["punto_conexion_sen_limpio"].map(sub_map_exact).astype("Int64")

    print("---------------------------------------------")
    print("NaN id_subestacion luego match exacto:", gx_out["id_subestacion"].isna().sum())
    print("---------------------------------------------")

    # 8) Fuzzy in-place
    fuzzy_fill_id_subestacion_inplace(
        gx=gx_out,
        subest=subest,
        threshold=90,
        scorer=fuzz.token_set_ratio,
        save_audit_xlsx=str(DATA_PROCESSED / "fuzzy_matches_subestaciones.xlsx"),
    )

    print("---------------------------------------------")
    print("NaN id_subestacion luego fuzzy:", gx_out["id_subestacion"].isna().sum())
    print("---------------------------------------------")

    # 9) Corrección manual POST (solo NaN)
    gx_out["central_norm"] = normalize_upper_no_accents_keep_enye(gx_out["central"])
    dict_reemplazo_norm = {
        normalize_upper_no_accents_keep_enye(pd.Series([k])).iloc[0]:
        normalize_upper_no_accents_keep_enye(pd.Series([v])).iloc[0]
        for k, v in dict_remplazo_central.items()
    }

    mask_manual = gx_out["id_subestacion"].isna()
    gx_out.loc[mask_manual, "punto_conexion_sen_limpio"] = (
        gx_out.loc[mask_manual, "punto_conexion_sen_limpio"]
        .fillna(gx_out.loc[mask_manual, "central_norm"].map(dict_reemplazo_norm))
    )
    gx_out.loc[mask_manual, "id_subestacion"] = (
        gx_out.loc[mask_manual, "punto_conexion_sen_limpio"].map(sub_map_exact).astype("Int64")
    )
    gx_out.drop(columns=["central_norm"], inplace=True, errors="ignore")

    print("---------------------------------------------")
    print("NaN id_subestacion luego manual:", gx_out["id_subestacion"].isna().sum())
    print("---------------------------------------------")

    # 10) Asegurar id_infotecnica si existe
    if "id_infotecnica" not in gx_out.columns:
        if "id" in gx_out.columns:
            gx_out["id_infotecnica"] = pd.to_numeric(gx_out["id"], errors="coerce").astype("Int64")
        else:
            gx_out["id_infotecnica"] = NA

    # 11) Renombrar central -> nombre_central
    gx_out.rename(columns={"central": "nombre_central"}, inplace=True)

    # 12) CSV completo (auditoría)
    gx_out.to_csv(
        OUT_FULL,
        encoding="utf-8",
        sep=";",
        index=False,
        lineterminator="\n",
        quotechar='"',
        quoting=1,
    )
    print(f"✅ CSV completo generado: {OUT_FULL}")

    # 13) Crear id_central sin merge
    centrales_df, id_central_series = build_id_central_no_merge(gx_out)
    gx_out["id_central"] = id_central_series

    print("---------------------------------------------")
    print("NaN id_central (debería ser 0):", gx_out["id_central"].isna().sum())
    print("---------------------------------------------")

    # 14) Export centrales.csv
    centrales_export = centrales_df.drop(columns=["_key_hash"], errors="ignore")

    centrales_export.to_csv(
        OUT_CENTRALES,
        encoding="utf-8",
        sep=";",
        index=False,
        lineterminator="\n",
        quotechar='"',
        quoting=1,
    )
    print(f"✅ centrales.csv generado: {OUT_CENTRALES} | filas={len(centrales_export)}")

    # 15) Export gx_real.csv
    # Ahora incluimos fecha_hora además de los identificadores.
    gx_real_fact = gx_out[["id_central", "nombre_unidadgen","id_version", "fecha_hora", "inyeccion_retiro"]].copy()

    gx_real_fact.to_csv(
        OUT_GX_REAL,
        encoding="utf-8",
        sep=";",
        index=False,
        lineterminator="\n",
        quotechar='"',
        quoting=1,
    )
    print(f"✅ gx_real.csv generado: {OUT_GX_REAL} | filas={len(gx_real_fact)}")

    print("---------------------------------------------")
    print("✅ Proceso terminado.")
    print("---------------------------------------------")


if __name__ == "__main__":
    main()