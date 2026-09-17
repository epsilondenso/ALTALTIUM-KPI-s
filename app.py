import streamlit as st
from datetime import timedelta
import pandas as pd

from panels.principal import panel_principal, load_table_from_sql
from panels.stats import stats_panel
from config.queries.main_panel import current_week
from src.db.connect import get_connection


# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(
        page_title="KPI's Altaltium",
        page_icon="📊",
        layout="wide"
    )

# ============================================================
# CONEXIÓN CON LA DB
# ============================================================
conn = get_connection()

# ============================================================
# SEMANA MÁS RECIENTE
# ============================================================
semana = load_table_from_sql(
    current_week,
    conn
)
fecha_inicio = semana["inicio_semana"].iloc[0]
fecha_fin = (
    semana["fin_semana"].iloc[0]
    + timedelta(days=1)
)

# ============================================================
# DICT PANEL
# ============================================================
panels = {
    "Principal": panel_principal,
    "Estad. por portal": stats_panel,
}
# ============================================================
# PANEL LATERAL
# ============================================================
with st.sidebar:

    st.header("Periodo")
    fecha_inicio = st.date_input(
        "Fecha inicial",
        value=semana["inicio_semana"].iloc[0]
    )
    fecha_fin = st.date_input(
        "Fecha final",
        value=semana["fin_semana"].iloc[0]
        + timedelta(days=1)
    )
    if fecha_inicio > fecha_fin:
        st.error(
            "La fecha inicial debe ser anterior a la fecha final."
        )
        st.stop()

    st.header("Panel")

    panel = st.selectbox(
        "Selecciona un panel",
        options=[
            "Principal",
            "Estad. por portal",
        ]
    )


st.title(panel)

st.caption(
    f"Periodo: {fecha_inicio:%d/%m/%Y} — "
    f"{fecha_fin:%d/%m/%Y}"
)


panels[panel](
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        conn=conn
    )

# ============================================================
# CSS GLOBAL
# ============================================================

st.markdown(
    """
    <style>

        /* ================================================== */
        /* SIDEBAR */
        /* ================================================== */

        [data-testid="stSidebar"] {
            min-width: 200px;
            max-width: 200px;
            background-color: #3B3B3B;
        }

        [data-testid="stSidebar"] > div:first-child {
            background-color: #3B3B3B;
        }


        /* ================================================== */
        /* TIPOGRAFÍA */
        /* ================================================== */

        html, body, [class*="css"] {
            font-family: Gotham, sans-serif;
        }

        h1, h2, h3 {
            font-family: Gotham, sans-serif;
        }

        [data-testid="stMetricValue"],
        [data-testid="stMetricLabel"] {
            font-family: Arial, sans-serif;
        }


        /* ================================================== */
        /* MARCOS DE LAS GRÁFICAS */
        /* ================================================== */

        [data-testid="stPlotlyChart"] {
            border: 1px solid #d9d9d9;
            border-radius: 12px;
            overflow: hidden;
        }


        /* ================================================== */
        /* FONDOS */
        /* ================================================== */

        .stApp {
            background-color: #000000;
        }


        /* ================================================== */
        /* BARRA SUPERIOR */
        /* ================================================== */

        [data-testid="stHeader"] {
            background-color: #52BEC0;
        }

        [data-testid="stHeader"] > div {
            background-color: #52BEC0;
        }

    </style>
    """,
    unsafe_allow_html=True
)