from src.db.connect import get_connection

from src.db.queries.semanas import insertar_siguiente_semana

from src.db.insert_table import insert_table

from src.clean_tables import load_table

from src.utils import get_files

from src.preprocessing import concat_tables

from config.paths import (
    SCHEMAS,
    CRM,
    CITAS,
    INTERESADOS,
    ESTAD_PORTALES,
)


def cargar_datos():

    ###################################
    #-- CARGAR TABLAS DESDE LOS CSV'S #
    ###################################

    # --------------------------------
    # -- leads_crm --
    # --------------------------------

    print("Cargando leads_crm")

    leads_crm_path = get_files(CRM)[0]

    crm_df = load_table(
        path=CRM / leads_crm_path,
        yaml_path=SCHEMAS / "leads_table.YAML",
        date_format= "%d/%m/%Y %H:%M",
        day_first=True
    )

    # --------------------------------
    # -- citas --
    # --------------------------------

    print("Cargando citas")

    citas_path = get_files(CITAS)[0]

    citas_df = load_table(
        path=CITAS / citas_path,
        yaml_path=SCHEMAS / "citas_table.YAML"
    )

    # --------------------------------
    # -- estadísticas --
    # --------------------------------

    print("Cargando estadísticas")

    concat_tables(
        dir=ESTAD_PORTALES,
        output=ESTAD_PORTALES / "stats.csv"
    )

    stats_df = load_table(
        path=ESTAD_PORTALES / "stats.csv",
        yaml_path=SCHEMAS / "stats.YAML"
    )

    # --------------------------------
    # -- interesados --
    # --------------------------------

    print("Cargando interesados")

    concat_tables(
        dir=INTERESADOS,
        output=INTERESADOS / "interesados.csv",
        add_portal_column=False
    )

    inter_df = load_table(
        path=INTERESADOS / "historico_inter_portales.csv",
        yaml_path=SCHEMAS / "interesados_table.YAML",
        date_format= "mixed",
        day_first=True
    )

    return [
        crm_df,
        citas_df,
        stats_df,
        inter_df,
    ]


def actualizar_db(tables):

    yamls = [
        "leads_table.YAML",
        "citas_table.YAML",
        "stats.YAML",
        "interesados_table.YAML",
    ]

    table_names = [
        "leads_crm",
        "citas",
        "stats_portales",
        "interesados",
    ]

    errores = []

    print("Estableciendo conexión con la db")

    conn = get_connection()

    print("Conexión establecida")

    # --------------------------------
    # -- semanas --
    # --------------------------------

    print("Actualizando tabla semanas")

    try:

        insertar_siguiente_semana(conn)

        conn.commit()

        print("Tabla de semanas actualizada")

    except Exception as error:

        conn.rollback()

        print("ERROR al actualizar tabla semanas")
        print(f"  {type(error).__name__}: {error}")

        errores.append("semanas")

    # --------------------------------
    # -- demás tablas --
    # --------------------------------

    for df, yaml, table_name in zip(
        tables,
        yamls,
        table_names
    ):

        print(f"Actualizando tabla {table_name}")

        try:

            insert_table(
                df,
                SCHEMAS / yaml,
                conn
            )

            print(f"Tabla {table_name} actualizada")

        except Exception as error:

            conn.rollback()

            print(f"ERROR al actualizar tabla {table_name}")
            print(f"  {type(error).__name__}: {error}")

            errores.append(table_name)

            continue

    # --------------------------------
    # -- resumen --
    # --------------------------------

    print()
    print("=" * 50)

    if errores:

        print("ACTUALIZACIÓN COMPLETADA CON ERRORES")
        print()
        print("Tablas que no pudieron actualizarse:")

        for table in errores:
            print(f"  - {table}")

    else:

        print("ACTUALIZACIÓN COMPLETADA")
        print()
        print("Todas las tablas fueron actualizadas correctamente.")

    print("=" * 50)

    conn.close()

    print("Sesión cerrada")


if __name__ == "__main__":

    print("=" * 50)
    print("ACTUALIZACIÓN DE BASE DE DATOS")
    print("=" * 50)

    try:

        tables = cargar_datos()

        actualizar_db(tables)

    except Exception as error:

        print()
        print("=" * 50)
        print("ERROR DURANTE LA CARGA DE DATOS")
        print("=" * 50)
        print(f"{type(error).__name__}: {error}")

        raise