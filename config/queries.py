current_week = """
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