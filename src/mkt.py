import pandas as pd
import numpy as np

def count_inter_day(inter_df: pd.DataFrame) -> pd.Series:

    """
    Cuenta y agrupa el número de interesados por día.

    Parameters
    ----------
    inter_df : pd.DataFrame
        DataFrame que contiene los interesados y sus fechas.

    Returns
    -------
    pd.Series
        Número de interesados agrupados por día.
    """

    inter_df["Fecha"] = pd.to_datetime(inter_df["Fecha"]).dt.strftime("%Y-%m-%d")
    grouped = inter_df.groupby(by = "Fecha").count()["Nombre y apellido"]

    return grouped

def join_inter_crm(crm_df: pd.DataFrame,
                   inter_df: pd.DataFrame, 
                   how: str = "inner") -> pd.DataFrame:


    """
    Concilia las tablas de interesados y CRM mediante un inner join.

    Parameters
    ----------
    crm_df : pd.DataFrame
        DataFrame con los registros del CRM.
    inter_df : pd.DataFrame
        DataFrame con los registros de interesados.

    Returns
    -------
    pd.DataFrame
        DataFrame resultante de unir ambas tablas por correo electrónico
        e identificador del aviso.
    """


    # CONCILIAR LAS TABLAS
    crm_df.rename(columns = {"Email":"E-mail", "ID de publicación": "Id aviso"}, inplace= True)
    crm_df = crm_df[crm_df["Portal origen"] == "Inmuebles24"].copy()
    s = pd.to_numeric(crm_df["Id aviso"], errors="coerce")

    crm_df["Id aviso"] = s.where(s.mod(1).eq(0), 0).fillna(0).astype(int)
    inter_df["Id aviso"] = (
    pd.to_numeric(inter_df["Id aviso"], errors="coerce")
    .fillna(0)
    .astype(int)
    )

    # INNER JOIN

    resultado = inter_df[["E-mail", "Sucursal", "Id aviso"]].merge(
    crm_df[["E-mail", "¿Fue traspasado?", "Código asesor", "Id aviso"]],
    on=["E-mail", "Id aviso"],
    how= how
    )
    
    return resultado

def add_unique_interested(estad_port_df: pd.DataFrame,
                         inter_df: pd.DataFrame, 
                         inplace: bool = True) -> pd.DataFrame:

    """
    Agrega el número de interesados por día a las estadísticas del portal.

    Parameters
    ----------
    estad_port_df : pd.DataFrame
        DataFrame con las estadísticas del portal.
    inter_df : pd.DataFrame
        DataFrame con los registros de interesados.
    inplace : bool, optional
        Indica si se debe modificar el DataFrame original.

    Returns
    -------
    pd.DataFrame
        DataFrame con la columna de interesados agregada.
    """

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

def reg_vs_inter(joined_df: pd.DataFrame,
                 tot_inter_df: pd.DataFrame,
                 decimals: int = 3) -> float:

    reg_inter = np.round(joined_df.shape[0]/tot_inter_df.loc["Interesados", "conteo"], decimals)
    return reg_inter

def tras_vs_reg(joined_df: pd.DataFrame) -> pd.DataFrame:

    traspasos = joined_df[joined_df["¿Fue traspasado?"] == "Sí"]
    tras_reg = np.round(traspasos.shape[0]/joined_df.shape[0], 3)

    return tras_reg