prod_cap_query = """
                    SELECT 
                        producto,
                        captacion,
                        COUNT(*) AS conteo 
                    FROM 
                        citas 
                    WHERE 
                        fecha_cita 
                    BETWEEN
                        %s AND %s
                    AND 
                        captacion NOT IN ('s/d', '?', 'S/D', 'S/d')
                    GROUP BY 
                        producto, captacion
                    ORDR BY
                        conteo
                    DESC;
                """