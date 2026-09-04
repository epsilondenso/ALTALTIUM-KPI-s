# KPIs

Proyecto para calcular indicadores y embudos de marketing, CRM, citas y ventas.

## Datos de entrada

Coloque los archivos del periodo que se analizará en estas carpetas, respetando los formatos esperados:

| Carpeta | Contenido |
| --- | --- |
| `data/estad_portales/` | Estadísticas de rendimiento por portal (`.xlsx`). |
| `data/interesados_im24/` | Exportaciones de interesados de Inmuebles24 (`.xlsx`). |
| `data/crm/` | Exportación de leads del CRM (`.csv`). |
| `data/citas/` | Control de citas de ventas (`.csv`). |

Los notebooks toman los archivos disponibles en cada carpeta. Para evitar mezclar periodos, deje únicamente los archivos que correspondan al análisis actual. Los nombres pueden variar, pero las columnas deben conservar la estructura de las exportaciones originales.

## Instalación

Se recomienda usar Python 3.10 o superior.

```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirementes.txt
pip install jupyter openpyxl
```

## Ejecución

1. Agregue los archivos fuente en las carpetas indicadas.
2. Desde la raíz del proyecto, inicie Jupyter:

   ```bash
   jupyter notebook
   ```

3. Abra y ejecute todas las celdas de los notebooks en este orden:

   1. `notebooks/kpis_mkt.ipynb`: embudos de marketing, interesados, registros y traspasos.
   2. `notebooks/kpis_crm.ipynb`: embudo completo, citas y flujo de leads.
   3. `notebooks/kpis_ventas.ipynb`: leads, citas y ventas por asesor.

Los notebooks deben ejecutarse desde la carpeta `notebooks/` dentro de Jupyter: `set_paths.py` configura el acceso al código y a los datos del proyecto.

## Estructura

- `src/`: funciones de carga, limpieza y cálculo de KPIs.
- `config/`: rutas de datos y configuraciones compartidas.
- `notebooks/`: análisis y resultados consultables.
