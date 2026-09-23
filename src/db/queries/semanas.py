import pandas as pd

def insertar_siguiente_semana(conn):
    with conn.cursor() as cursor:

        # Obtener la última semana registrada
        cursor.execute("""
            SELECT id_semana, inicio_semana, fin_semana
            FROM semanas
            ORDER BY id_semana DESC
            LIMIT 1;
        """)

        ultima_semana = cursor.fetchone()

        if ultima_semana is None:
            raise ValueError("La tabla 'semanas' está vacía.")

        id_semana, inicio, fin = ultima_semana

        # Calcular siguiente semana
        nueva_id = id_semana + 1
        nuevo_inicio = inicio + pd.Timedelta(weeks=1)
        nuevo_fin = fin + pd.Timedelta(weeks=1)

        # Insertar
        cursor.execute("""
            INSERT INTO semanas (
                id_semana,
                inicio_semana,
                fin_semana
            )
            VALUES (%s, %s, %s);
        """, (
            nueva_id,
            nuevo_inicio,
            nuevo_fin
        ))

    conn.commit()

    return nueva_id