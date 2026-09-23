# KPI's Altaltium

Dashboard de indicadores para el seguimiento de **marketing, CRM, citas y ventas** de Altaltium.

El proyecto utiliza **Streamlit** para la visualización de los indicadores y **PostgreSQL** para almacenar la información procesada. Los datos de las diferentes fuentes se limpian, transforman y cargan mediante un proceso ETL automatizado.

## Características

El dashboard permite consultar información de:

* Indicadores generales del funnel.
* Interesados y registros en CRM.
* Traspasos de leads.
* Flujo de leads.
* Estadísticas de rendimiento por portal.
* Citas y su estado.
* Información filtrada por periodo.

Actualmente el dashboard cuenta con los siguientes paneles:

1. **Principal** — indicadores generales, funnel y flujo de leads.
2. **Estad. por portal** — estadísticas de rendimiento de los portales.
3. **Citas** — información y distribución de citas.

---

## Tecnologías

* **Python 3.10+**
* **Streamlit**
* **PostgreSQL**
* **Pandas**
* **NumPy**
* **Plotly**
* **Psycopg2**
* **PyYAML**

Las versiones utilizadas por el proyecto se encuentran especificadas en `requirements.txt`.

---

## Estructura del proyecto

```text
ALTALTIUM-KPI-s/
│
├── app.py
├── requirements.txt
├── schema.sql
├── README.md
│
├── config/
│   ├── config.py
│   ├── paths.py
│   ├── queries/
│   │   ├── appt_panel.py
│   │   ├── main_panel.py
│   │   └── stats_panel.py
│   └── schemas/
│       ├── citas_table.YAML
│       ├── historico_citas.YAML
│       ├── interesados_table.YAML
│       ├── leads_table.YAML
│       └── stats.YAML
│
├── panels/
│   ├── principal.py
│   ├── stats.py
│   └── citas.py
│
├── scripts/
│   └── update_db.py
│
└── src/
    ├── clean_tables.py
    ├── preprocessing.py
    ├── utils.py
    │
    └── db/
        ├── connect.py
        ├── insert_table.py
        └── queries/
            └── semanas.py
```

### Descripción de los directorios

| Directorio | Descripción                                                                              |
| ---------- | ---------------------------------------------------------------------------------------- |
| `config/`  | Configuración, consultas SQL y esquemas YAML utilizados durante la carga de datos.       |
| `panels/`  | Componentes visuales de cada panel del dashboard.                                        |
| `scripts/` | Scripts ejecutables para automatizar procesos, principalmente la actualización de la BD. |
| `src/`     | Funciones de limpieza, transformación, conexión e inserción de datos.                    |

---

# Base de datos

El proyecto utiliza **PostgreSQL**.

El esquema de la base de datos se encuentra en:

```text
schema.sql
```

Las principales tablas son:

* `leads_crm`
* `citas`
* `interesados`
* `stats_portales`
* `portales`
* `semanas`

El archivo `schema.sql` contiene la definición de las tablas, llaves primarias y relaciones entre ellas.

## Crear la base de datos

Después de crear una base de datos PostgreSQL, puede cargarse el esquema mediante:

```bash
psql -U postgres -d kpis_altaltium -f schema.sql
```

Por ejemplo, en una instalación local:

```text
Base de datos: kpis_altaltium
Host: localhost
Puerto: 5432
Usuario: postgres
```

---

# Instalación

Se recomienda utilizar un entorno virtual.

### 1. Crear el entorno virtual

```bash
python -m venv .venv
```

### 2. Activar el entorno

En Windows:

```powershell
.venv\Scripts\activate
```

En Linux/macOS:

```bash
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

# Configuración de la conexión a PostgreSQL

El proyecto puede conectarse a una base de datos PostgreSQL local o a una base de datos remota.

La conexión se encuentra centralizada en:

```text
src/db/connect.py
```

## PostgreSQL local

Si no existe `DB_URL` en los secretos de Streamlit, el proyecto utiliza los parámetros de conexión locales definidos en `get_connection()`.

Los valores predeterminados son:

```text
Host: localhost
Port: 5432
Database: kpis_altaltium
User: postgres
```

La contraseña debe configurarse de acuerdo con la instalación local.

## Base de datos remota

Para utilizar una base de datos remota, puede configurarse `DB_URL` mediante los secretos de Streamlit.

Crear:

```text
.streamlit/secrets.toml
```

con:

```toml
DB_URL = "postgresql://usuario:contraseña@host/base_de_datos"
```

> El archivo `.streamlit/secrets.toml` está incluido en `.gitignore` y no debe subirse al repositorio.

---

# Carga y actualización de datos

Los archivos de entrada deben colocarse en las carpetas correspondientes definidas en `config/paths.py`.

Las principales fuentes son:

| Fuente                   | Descripción                                  |
| ------------------------ | -------------------------------------------- |
| `data/crm/`              | Exportaciones de leads del CRM.              |
| `data/citas/`            | Información de citas.                        |
| `data/estad_portales/`   | Estadísticas de los portales.                |
| `data/interesados_im24/` | Exportaciones de interesados de Inmuebles24. |

Los archivos `.csv` y `.xlsx` no deben incluirse en el repositorio.

El proceso de actualización se ejecuta mediante:

```bash
python -m scripts.update_db
```

Este proceso:

1. Localiza los archivos de entrada.
2. Limpia y transforma los datos.
3. Combina los archivos que corresponda.
4. Valida las columnas utilizando los esquemas YAML.
5. Actualiza la tabla `semanas`.
6. Inserta los datos en PostgreSQL.
7. Reporta las tablas que hayan presentado errores durante la actualización.

Los esquemas utilizados para interpretar los archivos se encuentran en:

```text
config/schemas/
```

---

# Ejecutar el dashboard (Local)

Desde la raíz del proyecto:

```bash
streamlit run app.py
```

Después de iniciar Streamlit, se mostrará la dirección local del dashboard, normalmente:

```text
http://localhost:8501
```

El periodo y el panel pueden seleccionarse desde la barra lateral.

---

# Despliegue (Desplegado)
### Link: https://altaltium-kpi-s-lrzh7jtgxpssbv5mfkqm3o.streamlit.app

El dashboard puede desplegarse utilizando **Streamlit Community Cloud**.

El despliegue requiere:

1. Un repositorio de GitHub con el proyecto.
2. Una base de datos PostgreSQL accesible desde Internet.
3. Las dependencias especificadas en `requirements.txt`.
4. La variable `DB_URL` configurada como secreto en Streamlit.

En Streamlit Cloud, configurar el secreto:

```toml
DB_URL = "postgresql://usuario:contraseña@host/base_de_datos"
```

El archivo `schema.sql` puede utilizarse para crear la estructura inicial de la base de datos antes del despliegue.

> Las credenciales de la base de datos nunca deben almacenarse directamente en el código ni en el repositorio.

---

# Flujo general del proyecto

El funcionamiento del sistema puede resumirse como:

```text
Archivos fuente
     │
     ▼
Limpieza y transformación
     │
     ▼
Validación mediante esquemas YAML
     │
     ▼
PostgreSQL
     │
     ▼
Consultas SQL
     │
     ▼
Streamlit
     │
     ├── Principal
     ├── Estad. por portal
     └── Citas
```

---

# Desarrollo

Para modificar el dashboard:

* Las consultas utilizadas por los paneles se encuentran en `config/queries/`.
* La lógica visual de cada panel se encuentra en `panels/`.
* Las funciones relacionadas con la base de datos se encuentran en `src/db/`.
* Los procesos de limpieza y transformación se encuentran en `src/clean_tables.py` y `src/preprocessing.py`.
* La configuración de rutas se encuentra en `config/paths.py`.

Los cambios al esquema de la base de datos deben reflejarse también en:

```text
schema.sql
```

y, cuando corresponda, en los archivos YAML de:

```text
config/schemas/
```

---

# Archivos ignorados

Los datos de entrada y las credenciales locales están excluidos del repositorio mediante `.gitignore`.

Entre ellos:

```text
*.csv
*.xlsx
.streamlit/secrets.toml
*.dump
```

Esto evita publicar información de los sistemas fuente o credenciales de acceso a la base de datos.
