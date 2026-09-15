import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from datetime import timedelta

from src.db.connect import get_connection
from config.queries import (full_funnel_query, flujo_leads_query, 
                            total_citas_query, desglose_citas_query,
                            leads_por_asesor_query, current_week)


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
        value=semana["fin_semana"].iloc[0]+timedelta(days = 1)
    )

    if fecha_inicio > fecha_fin:
        st.error("La fecha inicial debe ser anterior a la fecha final.")
        st.stop()


# ============================================================
# ENCABEZADO
# ============================================================

st.title("Panel principal")

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

full_funnel["x_visual"] = full_funnel["conteo"]**0.25 

# ============================================================
# TABLA FLUJO DE LEADS
# ============================================================

flujo_leads = load_table_from_sql(flujo_leads_query,
                                  conn,
                                  params = (fecha_inicio, fecha_fin))

# ============================================================
# TABLA TOTAL CITAS
# ============================================================

total_citas = load_table_from_sql(total_citas_query,
                                  conn,
                                  params = (fecha_inicio, fecha_fin))

# ============================================================
# TABLA DESGLOSE CITAS
# ============================================================

desglose_citas = load_table_from_sql(desglose_citas_query,
                                  conn,
                                  params = (fecha_inicio, fecha_fin))

# ============================================================
# TABLA LEADS POR ASESOR
# ============================================================
leads_asesor = load_table_from_sql(leads_por_asesor_query,
                                  conn,
                                  params = (fecha_inicio, fecha_fin))
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
        x=full_funnel["x_visual"],
        customdata=full_funnel["conteo"],
        texttemplate="%{customdata:,}",
        textinfo="none",
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
    height=410,          # más compacto verticalmente
    width = 100,
    margin=dict(
        l=10,
        r=10,
        t=50,
        b=10
    ),
    font=dict(
        family= "Arial",
        size=12           # tamaño general del gráfico
    ),
    paper_bgcolor="#3B3B3B",
    plot_bgcolor="#3B3B3B",
)

#=============================================================
#GRÁFICA FLUJO LEADS
#=============================================================

fig_flujo = go.Figure(
    go.Bar(
        x=flujo_leads["leads"],
        y=flujo_leads["conteo"],
        orientation="v",
        text=flujo_leads["conteo"],
        textposition="outside",
        texttemplate="%{text:,}",
        marker=dict(
                    color="#00FFFF"
                )
    )
)

fig_flujo.update_layout(
    title=dict(
        text="Flujo de leads",
        x=0.5,
        xanchor="center",
        font=dict(size=20)
    ),
    font=dict(
        family="Arial",
        size=12
    ),
    paper_bgcolor="#3B3B3B",
    plot_bgcolor="#3B3B3B",
    height=410,
    margin=dict(l=15, r=40, t=50, b=15),
    xaxis=dict(
        title=None,
        showgrid=False
    ),
    yaxis=dict(
        title=None
    )
)

#============================================================
#GRÁFICA TOTAL CITAS
#============================================================
colores = {
    "Atendidas": "#0080ff",
    "Reagendadas": "#FFC107",
    "Canceladas": "#F44336"
}
fig_citas = go.Figure(
    go.Pie(
        labels=total_citas["asistencia"],
        values=total_citas["conteo"],
        textinfo="label+percent",
        textposition="inside",
        hole=0.35,
        marker = dict(colors = [colores[estado] for estado in total_citas["asistencia"]])
    )
)

fig_citas.update_layout(
    title=dict(
        text="Total de citas",
        x=0.5,
        xanchor="center",
        font=dict(size=20)
    ),
    font=dict(
        family="Arial",
        size=12
    ),
    paper_bgcolor="#3B3B3B",
    plot_bgcolor="#3B3B3B",
    height=410,
    margin=dict(l=15, r=15, t=50, b=15),
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.1,
        xanchor="center",
        x=0.5
    )
)

#=============================================================
#GRÁFICA LEADS POR ASESOR
#=============================================================

fig_la = go.Figure(
    go.Bar(
        x=leads_asesor["leads"],
        y=leads_asesor["asesor"],
        orientation="h",
        text=leads_asesor["leads"],
        textposition="outside",
        texttemplate="%{text:,}",
        marker=dict(
                    color="#00FFFF"
                )
    )
)

fig_la.update_layout(
    title=dict(
        text="Leads por asesor",
        x=0.5,
        xanchor="center",
        font=dict(size=20)
    ),
    font=dict(
        family="Arial",
        size=12
    ),
    paper_bgcolor="#3B3B3B",
    plot_bgcolor="#3B3B3B",
    height=410,
    margin=dict(l=15, r=40, t=50, b=15),
    xaxis=dict(
        title=None,
        showgrid=False
    ),
    yaxis=dict(
        title=None
    )
)

# =============================================================
# GRÁFICA DESGLOSE DE CITAS POR ASESOR
# =============================================================

fig_desglose = go.Figure()

fig_desglose.add_trace(
    go.Bar(
        x=desglose_citas["asesor"],
        y=desglose_citas["atendidas"],
        name="Atendidas",
        marker=dict(color="#0080FF")
    )
)

fig_desglose.add_trace(
    go.Bar(
        x=desglose_citas["asesor"],
        y=desglose_citas["canceladas"],
        name="Canceladas",
        marker=dict(color="#F44336")
    )
)

fig_desglose.add_trace(
    go.Bar(
        x=desglose_citas["asesor"],
        y=desglose_citas["reagendadas"],
        name="Reagendadas",
        marker=dict(color="#FFC107")
    )
)

fig_desglose.update_layout(
    title=dict(
        text="Desglose de citas por asesor",
        x=0.5,
        xanchor="center",
        font=dict(size=20)
    ),
    font=dict(
        family="Arial",
        size=12
    ),
    paper_bgcolor="#3B3B3B",
    plot_bgcolor="#3B3B3B",
    height=410,
    margin=dict(
        l=15,
        r=15,
        t=50,
        b=15
    ),
    barmode="stack",
    xaxis=dict(
        title=None,
        showgrid=False,
        tickangle=-45
    ),
    yaxis=dict(
        title="Número de citas",
        showgrid=True
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.55,
        xanchor="center",
        x=0.5
    )
)

col1, col2, col3 = st.columns([0.95, 0.95, 0.95])

with col1:
    st.plotly_chart(fig, use_container_width=True)
with col2:
    st.plotly_chart(fig_flujo, use_container_width=True)
with col3:
    st.plotly_chart(fig_citas, use_container_width=True)

st.plotly_chart(fig_la, use_container_width=True)
st.plotly_chart(fig_desglose, use_container_width=True)
#=============================================================
#                            CSS
#=============================================================

st.markdown(
    """
    <style>
        [data-testid="stMetric"] {
            background-color: #52BEC0;
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

# ============================================================
# MARCOS GRÁFICAS
# ============================================================

st.markdown(
    """
    <style>
    [data-testid="stPlotlyChart"] {
        border: 1px solid #d9d9d9;
        border-radius: 12px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <style>
        /* Fondo principal */
        .stApp {
            background-color: #000000;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #3B3B3B;
        }

        [data-testid="stSidebar"] > div:first-child {
            background-color: #3B3B3B;
        }

        /* Barra superior */
        [data-testid="stHeader"] {
            background-color: #52BEC0;
        }

        /* Contenedor de la barra superior */
        [data-testid="stHeader"] > div {
            background-color: #52BEC0;
        }
    </style>
    """,
    unsafe_allow_html=True
)