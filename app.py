import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import timedelta

from src.db.connect import get_connection
from config.queries import full_funnel_query, current_week


def load_table_from_sql(
    consulta: str,
    conn,
    params: tuple | None = None
) -> pd.DataFrame:
    return pd.read_sql(
        consulta,
        conn,
        params=params
    )

def get_value(df: pd.DataFrame, etapa: str, column: str = "etapa") :

    value = df[df[column] == etapa]["conteo"].iloc[0]

    return value 


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="KPI's Altaltium",
    page_icon="📊",
    layout="wide"
)


# ============================================================
# CONEXIÓN
# ============================================================

conn = get_connection()


# ============================================================
# SEMANA MÁS RECIENTE
# ============================================================

semana = load_table_from_sql(current_week, conn)

fecha_inicio = semana["inicio_semana"].iloc[0]
fecha_fin = semana["fin_semana"].iloc[0] + timedelta(days = 1)


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
    )

    if fecha_inicio > fecha_fin:
        st.error("La fecha inicial debe ser anterior a la fecha final.")
        st.stop()


# ============================================================
# ENCABEZADO
# ============================================================

st.title("Dashboard de KPI's")

st.caption(
    f"Periodo: {fecha_inicio:%d/%m/%Y} — {fecha_fin:%d/%m/%Y}"
)


# ============================================================
# TABLA EMBUDO
# ============================================================

full_funnel = load_table_from_sql(
    full_funnel_query,
    conn,
    params=(fecha_inicio, fecha_fin)
)


# ============================================================
# TARJETAS KPI
# ============================================================

col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.metric(
    "Interesados",
    f"{get_value(full_funnel, "Interesados")}"
)

col2.metric(
    "Registrados CRM",
    f"{get_value(full_funnel, "Registrados")}"
)

col3.metric(
    "Tasa de registro",
    f"{round(100*get_value(full_funnel, "Registrados")/get_value(full_funnel, "Interesados"), 2)}%"
)

col4.metric(
    "Transferidos",
    f"{get_value(full_funnel, "Traspasados")}"
)

col5.metric(
    "Sin traspasar",
    f"{get_value(full_funnel, "Registrados") - get_value(full_funnel, "Traspasados")}"
)

col6.metric(
    "Tasa de traspaso",
    f"{round(100*get_value(full_funnel, "Traspasados") / get_value(full_funnel, "Registrados"), 2)}%"
)



# ============================================================
# GRÁFICA EMBUDO
# ============================================================

fig = go.Figure(
    go.Funnel(
        y=full_funnel["etapa"],
        x=full_funnel["conteo"],
        textinfo="value+percent previous",
        textposition="auto",
        textfont=dict(
            size=12,
            family="Arial"
        ),
        marker=dict(
            color="#00FFFF"
        ),
        connector=dict(
            line=dict(
                color="lightgray",
                width=1
            )
        )
    )
)

fig.update_layout(
    title=dict(
        text="Conversión total",
        font=dict(size=20),
        x = 0.5,
        xanchor = "center"
    ),
    height=450,          # más compacto verticalmente
    width = 100,
    margin=dict(
        l=10,
        r=10,
        t=50,
        b=10
    ),
    font=dict(
        family="Arial",
        size=12           # tamaño general del gráfico
    ),
    paper_bgcolor="#3B3B3B",
    plot_bgcolor="#3B3B3B",
)

col1, col2 = st.columns([1.2, 1.2])

with col1:
    st.plotly_chart(fig, use_container_width=True)

#=============================================================
#                            CSS
#=============================================================

st.markdown(
    """
    <style>
        [data-testid="stMetric"] {
            background-color: #DFDFE1;
            border: 1px solid #d9d9d9;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        [data-testid="stMetricLabel"] {
            background-color: #3B3B3B;
            color: #EBEBEE;
            font-size: 14px;
            font-weight: 600;
            padding: 8px 12px;
        }

        [data-testid="stMetricValue"] {
            color: #1f1f1f;
            font-size: 28px;
            font-weight: 700;
            padding: 10px 12px 14px 12px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# SIDEBAR
# ============================================================
st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {
            min-width: 200px;
            max-width: 200px;
        }
    </style>
    """,
    unsafe_allow_html=True
)
# ============================================================
# TIPOGRAFÍA
# ============================================================
st.markdown(
    """
    <style>
        /* Todo el dashboard */
        html, body, [class*="css"] {
            font-family: Gotham, sans-serif;
        }

        /* Título principal */
        h1 {
            font-family: Gotham, sans-serif;
        }

        /* Encabezados */
        h2, h3 {
            font-family: Gotham, sans-serif;
        }

        /* Tarjetas st.metric */
        [data-testid="stMetricValue"],
        [data-testid="stMetricLabel"] {
            font-family: Arial, sans-serif;
        }
    </style>
    """,
    unsafe_allow_html=True
)