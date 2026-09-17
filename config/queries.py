current_week =  """
                SELECT inicio_semana, fin_semana FROM semanas ORDER BY id_semana DESC LIMIT 1;
                """

full_funnel_query = """
                    WITH periodo_seleccionado AS (
    SELECT %s::date AS fecha_inicio,
           %s::date AS fecha_fin
)

SELECT 'Exposición' AS etapa, SUM(exposicion) AS conteo
FROM stats_portales, periodo_seleccionado
WHERE periodo BETWEEN fecha_inicio AND fecha_fin

UNION ALL

SELECT 'Visualizaciones', SUM(visualizaciones)
FROM stats_portales, periodo_seleccionado
WHERE periodo BETWEEN fecha_inicio AND fecha_fin

UNION ALL

SELECT 'Interesados', COUNT(email)
FROM interesados, periodo_seleccionado
WHERE fecha BETWEEN fecha_inicio AND fecha_fin

UNION ALL

SELECT 'Registrados', COUNT(*)
FROM leads_crm
INNER JOIN interesados
    ON leads_crm.email = interesados.email
    AND leads_crm.id_aviso = interesados.id_aviso
CROSS JOIN periodo_seleccionado
WHERE fecha_registro BETWEEN fecha_inicio AND fecha_fin

UNION ALL

SELECT 'Traspasados', COUNT(*)
FROM leads_crm
INNER JOIN interesados
    ON leads_crm.email = interesados.email
    AND leads_crm.id_aviso = interesados.id_aviso
CROSS JOIN periodo_seleccionado
WHERE fecha_registro BETWEEN fecha_inicio AND fecha_fin
  AND fue_traspasado IS TRUE

UNION ALL

SELECT 'Citas', COUNT(*)
FROM citas, periodo_seleccionado
WHERE fecha_cita BETWEEN fecha_inicio AND fecha_fin

UNION ALL

SELECT 'Ventas', SUM(ventas)
FROM citas, periodo_seleccionado
WHERE fecha_cita BETWEEN fecha_inicio AND fecha_fin;
"""

flujo_leads_query = """
WITH periodo_seleccionado AS (
    SELECT
        %s::date AS fecha_inicio,
        %s::date AS fecha_fin
)

SELECT 
    'Nuevos' AS Leads, 
    COUNT(id_lead) AS Conteo 
FROM 
    leads_crm,
    periodo_seleccionado
WHERE 
    fecha_registro BETWEEN fecha_inicio AND fecha_fin

UNION ALL

SELECT 
    'En seguimiento', 
    COUNT(*) 
FROM 
    leads_crm,
    periodo_seleccionado
WHERE 
    fecha_registro BETWEEN fecha_inicio AND fecha_fin
AND 
    dio_seguimiento IS TRUE

UNION ALL

SELECT 
    'Fin sin venta',
    COUNT(*)
FROM 
    leads_crm,
    periodo_seleccionado
WHERE
    fecha_registro BETWEEN fecha_inicio AND fecha_fin
AND
    hubo_venta_pago IS FALSE
AND
    abierto IS FALSE

UNION ALL

SELECT 
    'Estancados', 
    COUNT(*) 
FROM 
    leads_crm,
    periodo_seleccionado
WHERE 
    fecha_registro BETWEEN fecha_inicio AND fecha_fin
AND 
    dio_seguimiento IS TRUE
AND 
    fecha_fin - fecha_ultima_actividad > INTERVAL '3 days'
AND 
    abierto IS TRUE

ORDER BY
    Conteo DESC;
              """


total_citas_query = """
SELECT 
	INITCAP(asistencia || 's') AS Asistencia, 
	COUNT(asistencia) AS conteo 
FROM 
	citas 
WHERE 
	fecha_cita 
BETWEEN 
	%s AND %s 
AND
    asistencia in ('atendida', 'cancelada', 'reagendada')
GROUP BY 
	asistencia;
"""

leads_por_asesor_query = """
SELECT 
    traspasado_a as Asesor, 
    COUNT(*) as Leads 
FROM 
    leads_crm 
WHERE 
    fecha_registro 
BETWEEN 
    %s AND %s 
GROUP BY 
    Asesor 
ORDER BY 
    Leads ASC;

"""

desglose_citas_query = """
SELECT
    asesor AS Asesor,
    COUNT(*) FILTER (WHERE asistencia = 'atendida') AS Atendidas,
    COUNT(*) FILTER (WHERE asistencia = 'cancelada') AS Canceladas,
    COUNT(*) FILTER (WHERE asistencia = 'reagendada') AS Reagendadas,
	COUNT(*) AS Total
FROM citas
WHERE fecha_cita BETWEEN %s AND %s
GROUP BY asesor
ORDER BY Atendidas DESC;
"""