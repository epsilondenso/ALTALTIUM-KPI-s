import pandas as pd
import numpy as np

def count_inter_day(inter_df: pd.DataFrame) -> pd.Series:

    inter_df["Fecha"] = pd.to_datetime(inter_df["Fecha"]).dt.strftime("%Y-%m-%d")
    grouped = inter_df.groupby(by = "Fecha").count()["Nombre y apellido"]

    return grouped

def add_unique_interested(estad_port_df: pd.DataFrame,
                         inter_df: pd.DataFrame, 
                         inplace: bool = True) -> pd.DataFrame:

    n_inter = count_inter_day(inter_df)

    if inplace:
        estad_port_df["Interesados"] = n_inter.values
    else:
        copy = estad_port_df.copy()
        copy["Interesados"] = n_inter.values
        return copy


def embudo(raw_data: pd.DataFrame,            
           columns: list[str] = ["Exposición", "Visualizaciones", "Consultas recibidas"],
           pct_decimals: int = 3) -> pd.DataFrame:

    """
    Calcula las métricas de un embudo a partir de los datos proporcionados.

    Parameters
    ----------
    raw_data : pd.DataFrame
        Datos con las columnas del embudo.
    columns : list[str], optional
        Columnas que representan las etapas del embudo.
    pct_decimals : int, optional
        Número de decimales para los porcentajes.

    Returns
    -------
    pd.DataFrame
        DataFrame con el conteo, porcentaje respecto al total
        y porcentaje respecto a la etapa anterior.
    """

    dict_embudo = {column: {"conteo": 0, "pct_tot": 0, "pct_rel": 0}
                   for column in columns} 
    
    embudo = pd.DataFrame(
        dict_embudo
    ).T

    embudo["conteo"] = [raw_data.loc[:, column].sum() for column in columns]

    embudo["pct_tot"] = [np.round(embudo.loc[index, "conteo"]/embudo.loc[columns[0], "conteo"], pct_decimals) 
                         for index in embudo.index]
    
    embudo["pct_rel"] = [1] + [np.round(embudo.iloc[i].iloc[0]/embudo.iloc[i-1].iloc[0], pct_decimals) 
                             for i in range(1, len(embudo.index))]
    
    return embudo