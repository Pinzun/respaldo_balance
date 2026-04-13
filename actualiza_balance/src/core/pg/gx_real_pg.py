# gx_real_pg.py — versión PostgreSQL de gx_real.py
"""
La única diferencia con gx_real.py es la función extrae_data_subestacion,
que usa db_utils_pg en vez de db_utils. El resto de la lógica (transformar,
fuzzy matching, etc.) se importa bajo demanda desde gx_real.py al llamar main().
"""
import pandas as pd

from actualiza_balance.src.db.db_utils_pg import open_connection, close_connection


def extrae_data_subestacion() -> pd.DataFrame:
    """Extrae subestaciones desde PostgreSQL."""
    conn, tunnel, _ = open_connection()
    q = "SELECT * FROM mercado_corto_plazo.subestacion;"
    with conn.cursor() as cursor:
        cursor.execute(q)
        data = cursor.fetchall()
    close_connection(conn, tunnel)
    return pd.DataFrame(data)


def main():
    """
    Equivalente de gx_real.main() usando PostgreSQL.
    Importa gx_real bajo demanda para evitar dependencias de módulo en imports.
    """
    import os
    from actualiza_balance.src.core.mariaDB.gx_real import (
        load_csv_files,
        transformar,
        transformar_centrales,
        limpia_punto_conexion,
        normalize_upper_no_accents_keep_enye,
        fuzzy_fill_id_subestacion_inplace,
        build_id_central_no_merge,
        dict_remplazo_central,
        DATA_RAW,
        DATA_PROCESSED,
        DATA_CENTRALES,
        DATA_SUBESTACIONES,
        OUT_FULL,
        OUT_CENTRALES,
        OUT_GX_REAL,
    )
    from rapidfuzz import fuzz

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    OUT_GX_REAL.parent.mkdir(parents=True, exist_ok=True)

    gx_raw = load_csv_files(DATA_RAW)
    centrales_xlsx = pd.read_excel(DATA_CENTRALES, skiprows=6)

    if not os.path.exists(DATA_SUBESTACIONES):
        subest = extrae_data_subestacion()  # ← usa PostgreSQL
        subest.to_excel(DATA_SUBESTACIONES, index=False)
    else:
        subest = pd.read_excel(DATA_SUBESTACIONES)

    if "nombre" in subest.columns:
        subest["nombre"] = (
            subest["nombre"]
            .astype("string")
            .str.replace("Ã±", "Ñ", regex=False)
            .str.replace("Ã'", "Ñ", regex=False)
        )

    gx = transformar(gx_raw)
    cent = transformar_centrales(centrales_xlsx)
    gx_out = gx.merge(cent, how="left", left_on="central", right_on="nombre")
    gx_out = limpia_punto_conexion(gx_out)

    gx_out["punto_conexion_sen_limpio"] = normalize_upper_no_accents_keep_enye(
        gx_out["punto_conexion_sen_limpio"]
    )
    subest["nombre"] = normalize_upper_no_accents_keep_enye(subest["nombre"])

    sub_map_exact = (
        subest[["nombre", "id_subestacion"]]
        .dropna()
        .drop_duplicates(subset=["nombre"])
        .set_index("nombre")["id_subestacion"]
        .to_dict()
    )
    gx_out["id_subestacion"] = (
        gx_out["punto_conexion_sen_limpio"].map(sub_map_exact).astype("Int64")
    )

    fuzzy_fill_id_subestacion_inplace(
        gx=gx_out,
        subest=subest,
        threshold=90,
        scorer=fuzz.token_set_ratio,
        save_audit_xlsx=str(DATA_PROCESSED / "fuzzy_matches_subestaciones.xlsx"),
    )

    centrales_df, id_central_series = build_id_central_no_merge(gx_out)
    gx_out["id_central"] = id_central_series

    gx_out.to_csv(OUT_FULL, encoding="utf-8", sep=";", index=False,
                  lineterminator="\n", quotechar='"', quoting=1)

    centrales_export = centrales_df.drop(columns=["_key_hash"], errors="ignore")
    centrales_export.to_csv(OUT_CENTRALES, encoding="utf-8", sep=";", index=False,
                             lineterminator="\n", quotechar='"', quoting=1)

    gx_real_fact = gx_out[["id_central", "nombre_unidadgen", "id_version",
                             "fecha_hora", "inyeccion_retiro"]].copy()
    gx_real_fact.to_csv(OUT_GX_REAL, encoding="utf-8", sep=";", index=False,
                         lineterminator="\n", quotechar='"', quoting=1)

    print("✅ Proceso terminado (PostgreSQL).")


if __name__ == "__main__":
    main()
