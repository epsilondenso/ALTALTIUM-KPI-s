from pathlib import Path
import pandas as pd
import numpy as np
from src.preprocessing import concat_tables, get_df
from src.mkt import (embudo, add_unique_interested, join_inter_crm, tras_vs_reg)

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
                 include_interesados: bool = True
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



def desglose_citas_asesor(citas_df: pd.DataFrame, 
                          asesores: list[str]):

    test = citas_df.groupby(by = ["ASESOR", "ASISTENCIA"], 
                            as_index= False, 
                            observed = True).count().sort_values(by = "ASESOR", 
                                                                 ascending = False, 
                                                                 ignore_index = True).iloc[:, :3]

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


    return test, res_citas
