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
                    GROUP BY 
                        producto, captacion
                    ORDER BY
                        conteo
                    DESC;
                """