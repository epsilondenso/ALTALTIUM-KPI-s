from pathlib import Path
import pandas as pd
import numpy as np
from src.preprocessing import concat_tables, get_df
from src.mkt import (embudo, add_unique_interested, join_inter_crm, tras_vs_reg)
from src.utils import strip_df
from config.paths import INTERESADOS

def evci_pipeline(estad_portales: str|Path|pd.DataFrame, 
                  inter_portales: str|Path|pd.DataFrame,
                  pct_decimals: int = 3,
                  start: int  = 2,
                  stop: int = 4,
                  include_consultas: bool = False,
                  include_interesados: bool = True) -> pd.DataFrame:
    
    """
    Integra el flujo de marketing para un embudo de conversión.

    Parameters
    ----------
    estad_portales : str | Path | pd.DataFrame
        Estadísticas de rendimiento de los portales.
    inter_portales : str | Path | pd.DataFrame
        Registros de interesados provenientes de los portales.
    pct_decimals : int, optional
        Número de decimales para los porcentajes del embudo.
    start : int, optional
        Índice inicial de los archivos cuando se recibe un directorio.
    stop : int, optional
        Índice final de los archivos cuando se recibe un directorio.
    include_consultas : bool, optional
        Incluye la etapa de consultas recibidas. Por defecto es False.
    include_interesados : bool, optional
        Incluye la etapa de interesados. Por defecto es True.

    Returns
    -------
    pd.DataFrame
        Embudo de marketing con las etapas seleccionadas.
    """

    portales_stat = get_df(estad_portales, start=start, stop=stop).groupby(by = "Período").sum()
    portales_inter = get_df(inter_portales, start=start, stop=stop)

    add_unique_interested(estad_port_df= portales_stat,
                      inter_df= portales_inter,
                      inplace= True)


    columns = ["Exposición", "Visualizaciones"]
    if include_consultas:
        columns.append("Consultas recibidas")
    if include_interesados:
        columns.append("Interesados")

    embudo_evci = embudo(raw_data= portales_stat, 
                     columns= columns,
                     pct_decimals= pct_decimals)

    return embudo_evci

def irt_pipeline(crm_df: pd.DataFrame,
                 interesados: Path | str | pd.DataFrame,
                 decimals: int = 3,
                 start: int = 2,
                 stop: int = 4,
                 include_interesados: bool = True,
                 include_traspasos: bool = True
                 ) -> pd.DataFrame:
    """
    Integra el flujo de interesados, registros y traspasos.

    Parameters
    ----------
    crm_df : pd.DataFrame
        Registros del CRM.
    interesados : Path | str | pd.DataFrame
        Registros de interesados provenientes de los portales.
    decimals : int, optional
        Número de decimales para los porcentajes del embudo.
    start : int, optional
        Índice inicial de los archivos cuando se recibe un directorio.
    stop : int, optional
        Índice final de los archivos cuando se recibe un directorio.
    include_interesados : bool, optional
        Incluye la etapa de interesados. Por defecto es True.

    Returns
    -------
    pd.DataFrame
        Embudo de CRM con las etapas seleccionadas.
    """
    columns = ["Interesados", "Registrados", "Traspasados"]
    if not include_interesados:
        columns.remove("Interesados")
    if not include_traspasos:
        columns.remove("Traspasados")

    inter_df = get_df(interesados, start= start, stop = stop)
    crm_join_inter = join_inter_crm(crm_df= crm_df, inter_df= inter_df)

    interesados_tot = inter_df.shape[0]
    registrados = crm_join_inter.shape[0]
    traspasados = crm_join_inter[crm_join_inter["¿Fue traspasado?"] == "Sí"].shape[0]
    #tras_reg = tras_vs_reg(crm_join_inter)

    raw = pd.DataFrame({"Interesados": [interesados_tot], 
                        "Registrados": [registrados],
                        "Traspasados": [traspasados]})#, index = [0, 1, 2])

    return embudo(raw, columns, decimals)

def full_funnel_pipeline(estad_portales: str | Path | pd.DataFrame,
                         inter_portales: str | Path | pd.DataFrame,
                         crm_df: pd.DataFrame,
                         pct_decimals: int = 3,
                         start: int = 2,
                         stop: int = 4,
                         include_consultas: bool = False,
                         include_interesados: bool = True) -> pd.DataFrame:
    """
    Integra los embudos de marketing y CRM en un solo flujo de conversión.

    Parameters
    ----------
    estad_portales : str | Path | pd.DataFrame
        Estadísticas de rendimiento de los portales.
    inter_portales : str | Path | pd.DataFrame
        Registros de interesados provenientes de los portales.
    crm_df : pd.DataFrame
        Registros del CRM usados para identificar registros y traspasos.
    pct_decimals : int, optional
        Número de decimales para los porcentajes del embudo.
    start : int, optional
        Índice inicial de los archivos cuando se recibe un directorio.
    stop : int, optional
        Índice final de los archivos cuando se recibe un directorio.
    include_consultas : bool, optional
        Incluye la etapa de consultas recibidas. Por defecto es False.
    include_interesados : bool, optional
        Incluye la etapa de interesados. Por defecto es True.

    Returns
    -------
    pd.DataFrame
        Embudo con las etapas seleccionadas. Los porcentajes se calculan de
        forma continua respecto a la primera etapa y a la etapa anterior.
    """

    marketing_funnel = evci_pipeline(
        estad_portales=estad_portales,
        inter_portales=inter_portales,
        pct_decimals=pct_decimals,
        start=start,
        stop=stop,
        include_consultas=include_consultas,
        include_interesados=include_interesados,
    )
    crm_funnel = irt_pipeline(
        crm_df=crm_df,
        interesados=inter_portales,
        decimals=pct_decimals,
        start=start,
        stop=stop,
        include_interesados=include_interesados,
    )

    crm_counts = crm_funnel["conteo"].drop(index="Interesados", errors="ignore")
    counts = pd.concat([marketing_funnel["conteo"], crm_counts])
    raw_data = pd.DataFrame([counts.to_list()], columns=counts.index.to_list())

    return embudo(
        raw_data=raw_data,
        columns=counts.index.to_list(),
        pct_decimals=pct_decimals,
    )

def desglose_citas_asesor(citas_df: pd.DataFrame): 
                          #asesores: list[str]):
    """
    Desglosa las citas de cada asesor según su asistencia.

    Parameters
    ----------
    citas_df : pd.DataFrame
        DataFrame de citas con las columnas de asesor y asistencia.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        Conteos por asesor y asistencia, y resumen por estado de cita.
    """

    test = citas_df.groupby(by = ["ASESOR", "ASISTENCIA"], 
                            as_index= False, 
                            observed = True).count().sort_values(by = "ASESOR", 
                                                                 ascending = False, 
                                                                 ignore_index = True).iloc[:, :3]
    
                                                                 
    asesores = citas_df["ASESOR"].unique().tolist()

    desglose = {"atendida": {asesor: 0 for asesor in asesores},
                "reagendada" : {asesor: 0 for asesor in asesores},
                "cancelada": {asesor: 0 for asesor in asesores},
                "otros": {asesor: 0 for asesor in asesores}
                }
    
    estados = ["atendida", "reagendada", "cancelada"]

    

    for asesor in asesores:
        total_citas = test[test["ASESOR"] == asesor].loc[:, "ID"].sum()

        for status_cita in estados:

            resultado = test.loc[
                (test["ASESOR"] == asesor)
                & (test["ASISTENCIA"] == status_cita),
                "ID"
            ]

            if not resultado.empty:
                desglose[status_cita][asesor] = resultado.iloc[0]
            else:
                desglose[status_cita][asesor] = 0

        total_conocidos = sum(
        desglose[estado][asesor]
        for estado in estados
    )

        desglose["otros"][asesor] = (
        total_citas - total_conocidos
    )

    res_citas = pd.DataFrame(desglose)
    res_citas["total"] = res_citas.sum(axis = 1)


    return res_citas

def leads_totales_asesor(crm_df: pd.DataFrame) -> pd.DataFrame:

    """
    Calcula el número total de leads asignados a cada asesor.

    Parameters
    ----------
    crm_df : pd.DataFrame
        DataFrame con los registros de leads y su asesor asignado.

    Returns
    -------
    pd.DataFrame
        DataFrame con el total de leads asignados a cada asesor,
        ordenado de mayor a menor.
    """

    total_leads = crm_df[["ID Lead", 
                      "a quien fue traspasado"]].groupby(by = "a quien fue traspasado", 
                                                         as_index = False, 
                                                         observed = False).count().sort_values(by="ID Lead", 
                                                                                               ascending=False, 
                                                                                               ignore_index = True)
    strip_df(total_leads)
    total_leads.columns = ["asesor", "total_leads"]

    return total_leads

def ventas_asesor(citas_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula las ventas acumuladas por asesor.

    Parameters
    ----------
    citas_df : pd.DataFrame
        DataFrame de citas con las columnas de asesor y ventas.

    Returns
    -------
    pd.DataFrame
        Ventas totales agrupadas por asesor.
    """
    test_ventas = citas_df.groupby(by = "ASESOR",
                            as_index = False).sum()[["ASESOR", "VENTAS"]]

    return test_ventas


def leads_tot_vs_regis(crm_df: pd.DataFrame,
                       irt_pipeline_args: dict = {"interesados":  INTERESADOS,
                                                  "start" : 1,
                                                  "stop" : 4, 
                                                  "include_traspasos" : False}) -> pd.DataFrame:
    """
    Obtiene el conteo y proporción de leads respecto a registros.

    Parameters
    ----------
    crm_df : pd.DataFrame
        DataFrame con los registros del CRM.
    irt_pipeline_args : dict, optional
        Argumentos adicionales enviados a `irt_pipeline`.

    Returns
    -------
    pd.DataFrame
        Conteo y porcentaje total del embudo de leads y registros.
    """

    leads_vs_reg = irt_pipeline(crm_df= crm_df, 
             **irt_pipeline_args)[["conteo", "pct_tot"]]

    return leads_vs_reg


def citas_vs_regis(citas: pd.DataFrame, 
                   decimals: int = 3) -> pd.DataFrame:
    """
    Calcula el porcentaje de citas registradas en CRM.

    Parameters
    ----------
    citas : pd.DataFrame
        DataFrame de citas con la columna de estado en CRM.
    decimals : int, optional
        Número de decimales para el porcentaje.

    Returns
    -------
    pd.DataFrame
        Conteos y porcentajes de citas totales y registradas.
    """

    total_citas = citas.shape[0]
    citas_registradas = citas[citas["CRM"] == "Registrado"].shape[0]
    tot_vs_reg ={"total": {"conteo": total_citas, "pct": 100}, "registradas": {"conteo": citas_registradas, "pct": 0}}
    tot_vs_reg["registradas"]["pct"] = round((citas_registradas / total_citas) * 100, decimals)
    tot_vs_reg["total"]["conteo"] = total_citas
    tot_vs_reg["registradas"]["conteo"] = citas_registradas

    return pd.DataFrame(tot_vs_reg).T


def full_sales_funnel_pipeline(estad_portales: str | Path | pd.DataFrame,
                               inter_portales: str | Path | pd.DataFrame,
                               crm_df: pd.DataFrame,
                               citas_df: pd.DataFrame,
                               pct_decimals: int = 3,
                               start: int = 2,
                               stop: int = 4,
                               include_consultas: bool = False,
                               include_interesados: bool = True,
                               include_citas_registradas: bool = True) -> pd.DataFrame:
    """
    Integra las etapas de marketing, CRM, citas y ventas en un solo embudo.

    Parameters
    ----------
    estad_portales : str | Path | pd.DataFrame
        Estadísticas de rendimiento de los portales.
    inter_portales : str | Path | pd.DataFrame
        Registros de interesados provenientes de los portales.
    crm_df : pd.DataFrame
        Registros del CRM usados para identificar registros y traspasos.
    citas_df : pd.DataFrame
        DataFrame de citas previamente procesado con `load_citas_df`.
    pct_decimals : int, optional
        Número de decimales para los porcentajes del embudo.
    start : int, optional
        Índice inicial de los archivos cuando se recibe un directorio.
    stop : int, optional
        Índice final de los archivos cuando se recibe un directorio.
    include_consultas : bool, optional
        Incluye la etapa de consultas recibidas. Por defecto es False.
    include_interesados : bool, optional
        Incluye la etapa de interesados. Por defecto es True.
    include_citas_registradas : bool, optional
        Incluye la etapa de citas registradas en CRM. Por defecto es True.

    Returns
    -------
    pd.DataFrame
        Embudo continuo desde exposición hasta ventas, con las etapas
        seleccionadas y sus porcentajes totales y relativos.
    """

    conversion_funnel = full_funnel_pipeline(
        estad_portales=estad_portales,
        inter_portales=inter_portales,
        crm_df=crm_df,
        pct_decimals=pct_decimals,
        start=start,
        stop=stop,
        include_consultas=include_consultas,
        include_interesados=include_interesados,
    )
    citas_funnel = citas_vs_regis(citas=citas_df, decimals=pct_decimals)
    ventas = ventas_asesor(citas_df=citas_df)["VENTAS"].sum()

    citas_counts = pd.Series(
        {
            "Citas": citas_funnel.loc["total", "conteo"],
            "Citas registradas": citas_funnel.loc["registradas", "conteo"],
        }
    )
    if not include_citas_registradas:
        citas_counts = citas_counts.drop(index="Citas registradas")

    counts = pd.concat(
        [
            conversion_funnel["conteo"],
            citas_counts,
            pd.Series({"Ventas": ventas}),
        ]
    )
    raw_data = pd.DataFrame([counts.to_list()], columns=counts.index.to_list())

    return embudo(
        raw_data=raw_data,
        columns=counts.index.to_list(),
        pct_decimals=pct_decimals,
    )

def flujo_de_leads(
    crm_df: pd.DataFrame,
    inicio_periodo: str,
    fin_periodo: str,
    pct_decimals: int = 3
) -> pd.DataFrame:
    """
    Calcula métricas del flujo de leads en un periodo determinado.

    Parameters
    ----------
    crm_df : pd.DataFrame
        DataFrame con los registros y estados de los leads del CRM.
    inicio_periodo : str
        Fecha inicial del periodo de análisis.
    fin_periodo : str
        Fecha final del periodo de análisis.
    pct_decimals : int, optional
        Número de decimales para los porcentajes.

    Returns
    -------
    pd.DataFrame
        Conteos y porcentajes de leads totales, nuevos, en seguimiento,
        estancados y cerrados sin venta.
    """

    time_stamped = crm_df.copy()

    # Convertir fechas
    time_stamped["Fecha última actividad"] = pd.to_datetime(
        time_stamped["Fecha última actividad"],
        format="mixed",
        dayfirst=True
    )

    time_stamped["Fecha de registro"] = pd.to_datetime(
        time_stamped["Fecha de registro"],
        format="mixed",
        dayfirst=True
    )

    inicio_periodo = pd.to_datetime(
        inicio_periodo,
        dayfirst=True
    )

    fin_periodo = pd.to_datetime(
        fin_periodo,
        dayfirst=True
    )

    # Totales
    totales = time_stamped.shape[0]

    # Nuevos
    nuevos = time_stamped[
        (time_stamped["Fecha de registro"] >= inicio_periodo) &
        (time_stamped["Fecha de registro"] <= fin_periodo)
    ].shape[0]

    # Seguimiento
    seguimiento = time_stamped[
        time_stamped["¿Dio seguimiento?"] == "Sí"
    ].shape[0]

    # Estancados
    estancados = time_stamped[
        (time_stamped["¿Dio seguimiento?"] == "Sí") &
        (
            fin_periodo - time_stamped["Fecha última actividad"]
            > pd.Timedelta(days=3)
        )
    ].shape[0]

    # Fin sin venta
    fin_sin_venta = time_stamped[
        (time_stamped["Estatus final"] == "closed") &
        (time_stamped["¿Hubo venta con pago?"] == "No")
    ].shape[0]

    # Crear DataFrame
    resultado = pd.DataFrame(
        {
            "conteo": [
                totales,
                nuevos,
                seguimiento,
                estancados,
                fin_sin_venta
            ]
        },
        index=[
            "totales",
            "nuevos",
            "seguimiento",
            "estancados",
            "fin_sin_venta"
        ]
    )

    # Porcentaje respecto al total
    resultado["pct"] = (resultado["conteo"] / totales).round(pct_decimals)

    return resultado
