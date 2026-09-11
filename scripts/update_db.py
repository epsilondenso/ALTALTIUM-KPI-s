from src.db.connect import get_connection
from src.db.queries.semanas import insertar_siguiente_semana
from src.db.insert_table import insert_table
from src.clean_tables import load_table
from src.utils import get_files
from src.preprocessing import concat_tables
from config.paths import SCHEMAS, CRM, CITAS, INTERESADOS, ESTAD_PORTALES


if __name__ == "__main__":

    ###################################
    #--CARGAR TABLAS DESDE LOS CSV'S--#
    ###################################
        # -- leads_crm -- # 
    leads_crm_path = get_files(CRM)[0]
    crm_df = load_table(path = CRM/leads_crm_path,
                        yaml_path = SCHEMAS/"leads_table.YAML",
                        date_format= "%d/%m/%Y %H:%M",
                        day_first=True)
        # -- citas -- # 
    citas_path = get_files(CITAS)[0]
    citas_df = load_table(path = CITAS / citas_path,
                          yaml_path= SCHEMAS/ "citas_table.YAML")
        # -- Estadísticas -- #
    stats_tables = get_files(ESTAD_PORTALES)
    concat = concat_tables(dir = ESTAD_PORTALES, #CONCATENAR LAS TABLAS Y GUARDAR como CSV
                           output = ESTAD_PORTALES / "stats.csv")
    
    stats_df = load_table(path = ESTAD_PORTALES / "stats.csv",
                          yaml_path= SCHEMAS / "stats.YAML"
                          )
        # -- Interesados -- #
    inter_tables = get_files(INTERESADOS)
    concat_inter = concat_tables(dir = INTERESADOS, #CONCATENAR LAS TABLAS Y GUARDAR como CSV
                                 output = INTERESADOS / "interesados.csv",
                                 add_portal_column= False)
    
    inter_df = load_table(path = INTERESADOS / "interesados.csv",
                          yaml_path= SCHEMAS / "interesados_table.YAML"
                          )
    tables = [crm_df, citas_df, stats_df, inter_df]
    yamls = ["leads_table.YAML", "citas_table.YAML", "stats.YAML", "interesados_table.YAML"]
    table_names = ["leads_crm", "citas", "stats_portales", "interesados"]

    ################################
    #--ACTUALIZAR TABLAS DE LA DB--#
    ################################
    print(f"Estableciendo conexión con la db")
    #time.sleep(3)
    conn = get_connection()
    print("Conexión establecida")
    print("Actualizando tabla semanas")
    #time.sleep(3)
    insertar_siguiente_semana(conn)
    conn.commit()
    #conn.close()
    print("Tabla de semanas actualizada")
    for i in range(len(tables)):
        print(f"Actualizando tabla {table_names[i]}")
        try:
            conn = get_connection()
            insert_table(
                tables[i],
                SCHEMAS/yamls[i],
                conn
                )
            print(f"Tabla {table_names[i]} actualizada")
        except:
            print("Ocurrió algún error")
            raise
    #time.sleep(3)
    print("Sesión cerrada") 
