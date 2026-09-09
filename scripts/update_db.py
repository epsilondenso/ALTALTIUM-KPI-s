import time
import yaml
import pandas as pd
from src.db.connect import get_connection
from src.db.queries.semanas import insertar_siguiente_semana
from src.db.insert_table import insert_table
from src.clean_tables import load_table
from src.utils import get_files
from config.paths import SCHEMAS, DATA, CRM, CITAS, INTERESADOS, ESTAD_PORTALES


if __name__ == "__main__":

    ###################################
    #--CARGAR TABLAS DESDE LOS CSV'S--#
    ###################################
    leads_crm_path = get_files(CRM)[1]
    crm_df = load_table(path = CRM/leads_crm_path,
           yaml_path = SCHEMAS/"leads_table.YAML")
    crm_df

    ################################
    #--ACTUALIZAR TABLAS DE LA DB--#
    ################################
    print(f"Estableciendo conexión con la db")
    #time.sleep(3)
    conn = get_connection()
    print("Conexión establecida")
    print("Actualizando tabla de semanas")
    #time.sleep(3)
    insertar_siguiente_semana(conn)
    conn.commit()
    print("Tabla de semanas actualizada")
    print("Actualizando tabla leads_crm")
    try:
        insert_table(
            crm_df,
            SCHEMAS/"leads_table.YAML",
            conn
            )
    except:
        print("Ocurrió algún error")
        raise
    #time.sleep(3)

    
    print("Sesión cerrada") 
