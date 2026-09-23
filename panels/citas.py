import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from config.config import portals_names

from config.queries.appt_panel import (prod_cap_query
                                        )

from panels.principal import load_table_from_sql

def panel_citas(fecha_inicio: str, fecha_fin: str, conn):

    prod_cap_table = load_table_from_sql(consulta= prod_cap_query,
                                         conn= conn,
                                         params = (fecha_inicio, fecha_fin))

    fig = px.bar(
    prod_cap_table,
    x="captacion",
    y="conteo",
    color="producto",
    barmode="stack",
    text="conteo"
    )

    fig.update_traces(
        textposition="outside",
        textfont=dict(size=12)
    )

    fig.update_layout(
        title=dict(
        text="Captación por producto",
        x=0.5,
        xanchor="center"
                        ),
        xaxis_title="Captación",
        yaxis_title="Conteo",
        font=dict(family="Gotham, Arial"),
        plot_bgcolor="#C90000",
        paper_bgcolor="#C90000",
        font_color="white",
        legend_title_text="Prodcuto",
        margin=dict(l=20, r=20, t=50, b=20)
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor="#29253A",
        zeroline=False
    )

    st.plotly_chart(fig, use_container_width=True)