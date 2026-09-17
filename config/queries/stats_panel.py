exposicion_query =  """
                    SELECT id_portal, periodo, exposicion
                    FROM stats_portales
                    WHERE periodo BETWEEN %s AND %s
                    ORDER BY id_portal, periodo ASC
                    """

vis_query = """
            SELECT id_portal, periodo, visualizaciones
            FROM stats_portales
            WHERE periodo BETWEEN %s AND %s
            ORDER BY id_portal, periodo ASC
            """


consultas_query =   """
                    SELECT id_portal, periodo, consultas_recibidas
                    FROM stats_portales
                    WHERE periodo BETWEEN %s AND %s
                    ORDER BY id_portal, periodo ASC
                    """

interesados_query = """
                    SELECT
                        id_portal,
                        fecha::date AS fecha,
                        COUNT(id_portal) AS interesados_recibidos
                    FROM interesados
                    WHERE fecha BETWEEN %s AND %s
                    GROUP BY id_portal, fecha::date
                    ORDER BY id_portal, fecha::date ASC;
                    """


embudo_query = """
                WITH periodo_seleccionado AS (
                SELECT
                        %s::date AS fecha_inicio,
                        %s::date AS fecha_fin
                )

                SELECT
                    id_portal,
                    'Exposición' AS etapa,
                    SUM(exposicion) AS conteo
                FROM stats_portales, periodo_seleccionado
                WHERE periodo BETWEEN fecha_inicio AND fecha_fin
                GROUP BY id_portal

                UNION ALL

                SELECT
                    id_portal,
                    'Visualizaciones' AS etapa,
                    SUM(visualizaciones) AS conteo
                FROM stats_portales, periodo_seleccionado
                WHERE periodo BETWEEN fecha_inicio AND fecha_fin
                GROUP BY id_portal

                UNION ALL

                SELECT
                    id_portal,
                    'Interesados' AS etapa,
                    COUNT(email) AS conteo
                FROM interesados, periodo_seleccionado
                WHERE fecha BETWEEN fecha_inicio AND fecha_fin
                GROUP BY id_portal

                ORDER BY id_portal ASC, conteo DESC;
                """
consultas_por_tipo_query =    """
                        SELECT 
                        	id_portal, 
                        	SUM(completaron_formulario) AS formulario,
                        	SUM(contactaron_por_whatsapp) AS Whatsapp, 
                        	SUM(vieron_tus_datos) AS vieron_tus_datos 
                        FROM 
                        	stats_portales 
                        WHERE 
                        	periodo 
                        BETWEEN 
                        	%s AND %s 
                        GROUP BY 
                        	id_portal;
                        """