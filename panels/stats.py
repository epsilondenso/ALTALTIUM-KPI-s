import plotly.graph_objects as go
import streamlit as st
from config.config import portals_names

from config.queries.stats_panel import (exposicion_query, 
                                        vis_query, 
                                        interesados_query, 
                                        embudo_query, 
                                        consultas_por_tipo_query)

from panels.principal import load_table_from_sql

colors = {1: "#adff00",
          2: "#FF084A",
          3: "#084AFF", 
          4: "#08C6FF"}

pie_colors = {"whatsapp": "#25d366",
              "formulario": "#3b5998",
              "vieron_tus_datos": "#1da1f2"


}

def stats_panel(fecha_inicio: str, fecha_fin: str, conn):

    def crear_grafica(
        df,
        columna_y,
        titulo,
        titulo_y,
        date_column: str = "periodo"
    ):

        fig = go.Figure()

        for id_portal, grupo in df.groupby("id_portal"):

            grupo = grupo.sort_values(date_column)

            color = colors[id_portal]

            fig.add_trace(
                go.Scatter(
                    x=grupo[date_column],
                    y=grupo[columna_y],
                    mode="lines+markers",
                    name=f"{portals_names[id_portal]}",

                    line=dict(
                        width=2,
                        color=color
                    ),

                    marker=dict(
                        size=5
                    ),

                    hovertemplate=(
                        "<b>%{fullData.name}</b><br>"
                        "Fecha: %{x|%d/%m/%Y}<br>"
                        f"{titulo_y}: %{{y:,}}"
                        "<extra></extra>"
                    )
                )
            )

        fig.update_layout(

            title=dict(
                text=titulo,
                font=dict(size=20),
                x=0.5,
                xanchor="center"
            ),

            height=400,

            margin=dict(
                l=10,
                r=10,
                t=50,
                b=10
            ),

            font=dict(
                family="Arial",
                size=12
            ),

            paper_bgcolor="#3B3B3B",
            plot_bgcolor="#3B3B3B",

            legend=dict(
                orientation="v",
                yanchor="bottom",
                y=0.5,
                xanchor="center",
                x=1.05
            )
        )

        fig.update_xaxes(
            title_text="Fecha",
            showgrid=True
        )

        fig.update_yaxes(
            title_text=titulo_y,
            showgrid=True,
            gridcolor="#555555",
            tickformat=","
        )

        return fig

    def crear_grafica_barras(
    df,
    titulo,
    titulo_y
):
        df = df.sort_values("id_portal")

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=[
                    portals_names[id_portal]
                    for id_portal in df["id_portal"]
                ],
                y=df["conteo"],
                marker=dict(
                    color=[
                        colors[id_portal]
                        for id_portal in df["id_portal"]
                    ]
                ),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    f"{titulo_y}: %{{y:,}}"
                    "<extra></extra>"
                ),
                text=df["conteo"],
                texttemplate="%{text:,}",
                textposition="outside"
            )
        )

        fig.update_layout(
            title=dict(
                text=titulo,
                font=dict(size=18),
                x=0.5,
                xanchor="center"
            ),
            height=400,
            margin=dict(
                l=10,
                r=10,
                t=50,
                b=10
            ),
            font=dict(
                family="Arial",
                size=12
            ),
            paper_bgcolor="#3B3B3B",
            plot_bgcolor="#3B3B3B",
            showlegend=False
        )

        fig.update_xaxes(
            title_text="Portal",
            showgrid=False,
            tickangle = -45
        )

        fig.update_yaxes(
            title_text=titulo_y,
            showgrid=True,
            gridcolor="#555555",
            tickformat=","
        )

        return fig

        # ============================================================
    
    def crear_pastel_interacciones(df, id_portal):

        fila = df[df["id_portal"] == id_portal].iloc[0]

        etiquetas = [
            "Formulario",
            "WhatsApp",
            "Vieron tus datos"
        ]

        valores = [
            fila["formulario"],
            fila["whatsapp"],
            fila["vieron_tus_datos"]
        ]

        fig = go.Figure(
            go.Pie(
                labels=etiquetas,
                values=valores,
                textinfo="value",
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "Interacciones: %{value:,}<br>"
                    "Proporción: %{percent}"
                    "<extra></extra>"
                ),
                hole=0.35,
                marker=dict(
                            colors=[
                                    pie_colors[inter]
                                    for inter in df.columns[1:]
                                ]
                            )
            )
        )

        fig.update_layout(
            title=dict(
                text=f"{portals_names[id_portal]}",
                font=dict(size=18),
                x=0.5,
                xanchor="center"
            ),
            height=350,
            margin=dict(
                l=10,
                r=10,
                t=50,
                b=10
            ),
            font=dict(
                family="Arial",
                size=11
            ),
            paper_bgcolor="#3B3B3B",
            plot_bgcolor="#3B3B3B",
            legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.25,
                        xanchor="center",
                        x=0.5),
            showlegend=True
        )

        return fig

    #=============================================================
    # BARRAS POR PORTAL
    # ============================================================

    df = load_table_from_sql(
        consulta= embudo_query,
        conn= conn,
        params= (fecha_inicio, fecha_fin)
    )
    exposicion_df = df[df["etapa"] == "Exposición"]
    visualizaciones_df = df[df["etapa"] == "Visualizaciones"]
    interesados_df = df[df["etapa"] == "Interesados"]

    col1, col2, col3 = st.columns(3)

    with col1:
        fig_exposicion = crear_grafica_barras(
            df=exposicion_df,
            titulo="Exposición",
            titulo_y="Exposición"
        )

        st.plotly_chart(
            fig_exposicion,
            use_container_width=True
        )


    with col2:
        fig_visualizaciones = crear_grafica_barras(
            df=visualizaciones_df,
            titulo="Visualizaciones",
            titulo_y="Visualizaciones"
        )

        st.plotly_chart(
            fig_visualizaciones,
            use_container_width=True
        )


    with col3:
        fig_interesados = crear_grafica_barras(
            df=interesados_df,
            titulo="Interesados",
            titulo_y="Interesados"
        )

        st.plotly_chart(
            fig_interesados,
            use_container_width=True
        )

    # ============================================================
    # CONSULTAS POR TIPO
    # ============================================================

    st.header("Consultas por tipo")

    cons_tipo_df = load_table_from_sql(consulta= consultas_por_tipo_query,
                                       conn= conn,
                                       params= (fecha_inicio, fecha_fin))
    col1, col2, col3, col4  = st.columns(4)

    for col, id_portal in zip([col1, col2, col3, col4], [1, 2, 3, 4]):
        with col:
            fig = crear_pastel_interacciones(
                cons_tipo_df,
                id_portal
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )
    st.header("Tendencias")
    # ============================================================
    # EXPOSICIÓN
    # ============================================================

    exp_df = load_table_from_sql(
        consulta=exposicion_query,
        conn=conn,
        params=(fecha_inicio, fecha_fin)
    )

    exp_fig = crear_grafica(
        df=exp_df,
        columna_y="exposicion",
        titulo="Exposición",
        titulo_y="Exposición"
    )

    st.plotly_chart(
        exp_fig,
        use_container_width=True
    )


    # ============================================================
    # VISUALIZACIONES
    # ============================================================
  
    vis_df = load_table_from_sql(
        consulta=vis_query,
        conn=conn,
        params=(fecha_inicio, fecha_fin)
    )

    vis_fig = crear_grafica(
        df=vis_df,
        columna_y="visualizaciones",
        titulo="Visualizaciones",
        titulo_y="Visualizaciones"
    )

    st.plotly_chart(
        vis_fig,
        use_container_width=True
    )

   # ============================================================
    # INTERESADOS
    # ============================================================
  
    cons_df = load_table_from_sql(
        consulta=interesados_query,
        conn=conn,
        params=(fecha_inicio, fecha_fin)
    )

    consultas_fig = crear_grafica(
        df=cons_df,
        columna_y="interesados_recibidos",
        titulo="Interesados",
        titulo_y="Interesados",
        date_column= "fecha"
    )

    st.plotly_chart(
        consultas_fig,
        use_container_width=True
    )
