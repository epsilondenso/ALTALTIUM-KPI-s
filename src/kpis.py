from pathlib import Path
import pandas as pd
import numpy as np
from src.preprocessing import concat_tables
from src.mkt import (embudo, add_unique_interested, join_inter_crm, tras_vs_reg)


def get_df(object: str|Path|pd.DataFrame, start: int = 2, stop: int = 4) -> pd.DataFrame:

        if isinstance(object, Path):
            return concat_tables(dir = object, start = start, stop = stop)
        
        elif isinstance(object, str):
            return pd.read_excel(object)
        
        else:
            return object


def evci_pipeline(estad_portales: str|Path|pd.DataFrame, 
                  inter_portales: str|Path|pd.DataFrame,
                  pct_decimals: int = 3,
                  start: int  = 2,
                  stop: int = 4):
    
    """
    Integra todo el flujo para el embudo de
    Exp -> Vis -> Cons -> Inter
    """

    portales_stat = get_df(estad_portales, start=start, stop=stop).groupby(by = "Período").sum()
    portales_inter = get_df(inter_portales, start=start, stop=stop)

    add_unique_interested(estad_port_df= portales_stat,
                      inter_df= portales_inter,
                      inplace= True)


    embudo_evci = embudo(raw_data= portales_stat, 
                     columns= ["Exposición", "Visualizaciones", "Consultas recibidas", "Interesados"],
                     pct_decimals= pct_decimals)

    return embudo_evci

def irt_pipeline(crm_df: pd.DataFrame,
                 interesados = Path|str|pd.DataFrame,
                 decimals: int = 3,
                 start: int = 2,
                 stop: int = 4
                 ):
    """
    Integra todo el flujo para 
    Interesados  vs Registros vs Traspasos
    """
    columns = ["Interesados", "Registrados", "Traspasados"]

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
                         stop: int = 4) -> pd.DataFrame:
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

    Returns
    -------
    pd.DataFrame
        Embudo con las etapas Exposición, Visualizaciones, Consultas
        recibidas, Interesados, Registrados y Traspasados. Los porcentajes
        se calculan de forma continua respecto a la primera etapa y a la
        etapa anterior.
    """

    marketing_funnel = evci_pipeline(
        estad_portales=estad_portales,
        inter_portales=inter_portales,
        pct_decimals=pct_decimals,
        start=start,
        stop=stop,
    )
    crm_funnel = irt_pipeline(
        crm_df=crm_df,
        interesados=inter_portales,
        decimals=pct_decimals,
        start=start,
        stop=stop,
    )

    counts = pd.concat(
        [marketing_funnel["conteo"], crm_funnel["conteo"].iloc[1:]]
    )
    raw_data = pd.DataFrame([counts.to_list()], columns=counts.index.to_list())

    return embudo(
        raw_data=raw_data,
        columns=counts.index.to_list(),
        pct_decimals=pct_decimals,
    )

