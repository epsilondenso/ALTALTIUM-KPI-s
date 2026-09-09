import time
from src.db.connect import get_connection
from src.db.queries.semanas import insertar_siguiente_semana

if __name__ == "__main__":
    print(f"Estableciendo conexión con la db")
    #time.sleep(3)
    conn = get_connection()
    print("Conexión establecida")
    print("Actualizando tabla de semanas")
    #time.sleep(3)
    insertar_siguiente_semana(conn)
    print("Tabla de semanas actualizada")
    #time.sleep(3)
    conn.commit()
    print("Sesión cerrada") 
