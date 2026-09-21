from pathlib import Path
import pandas as pd
from src.utils import get_files
from config.config import codif_sucursales


def concat_tables(dir: str|Path, 
                       output: str|Path|None = None,
                       return_concat: bool = True,
                       add_portal_column: bool =  True) -> pd.DataFrame|None :

    """
    Concatena tablas de Excel encontradas en un directorio.

    Parameters
    ----------
    dir : str | Path
        Directorio que contiene las tablas de Excel.
    start : int, optional
        Índice inicial de los archivos a concatenar.
    stop : int, optional
        Índice final de los archivos a concatenar.
    output : str | Path | None, optional
        Ruta donde se guardará la tabla concatenada. Si es None, no se guarda.
    return_concat : bool, optional
        Indica si se debe retornar la tabla concatenada.

    Returns
    -------
    pd.DataFrame | None
        Tabla concatenada, o None si `return_concat` es False.
    """
    #CARGAR TABLAS QUE TERMINAN EN .xlsx
    files = get_files(dir)
    tables = [pd.read_excel(dir /file, engine="openpyxl")  for file in files if file[-5:] == ".xlsx"]

    #AÑADIR COLUMNA id_portal LOS ARCHIVOS DEBEN ESTAR EN ORDEN 
    if add_portal_column:
        for i in range(len(tables)):
            tables[i]["id_portal"] = pd.Series(i+1, index=tables[i].index)
    concat = pd.concat(tables)
    #GUARDAR LA CONCATENACIÓN EN LA RUTA ESPECIFICADA
    if output is not None:
        concat.to_csv(path_or_buf= output, index= False)
    return concat if return_concat else None 


###########################
#-----REFACTORIZACIÓN-----#
###########################

def map_n_citas(n_citas_column: pd.Series) -> pd.Series:
                
    return n_citas_column.apply(lambda x: int(x[-1]))

def map_ventas(ventas_column: pd.Series) -> pd.Series:

    return ventas_column.fillna(0, inplace = False).apply(lambda x: 1 if not isinstance(x, int) else x)

def norm_asistencia(asistencia_column: pd.Series) -> pd.Series:

    return asistencia_column.str.lower().str.replace(" ", "", regex=False).str.replace(r"o$", "a", regex=True)

def limpiar_precio(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.str.replace(r"\D", "", regex=True),
        errors="coerce"
    ).astype("Int64")

def fillnull(series: pd.Series) -> pd.Series:

    return series.fillna(0)

def codificar_portales(sucursal_col: pd.Series) -> pd.Series:

    return sucursal_col.apply(lambda x: codif_sucursales[x]).astype("Int64")



transformations = {
    "mapear n citas" : map_n_citas,
    "mapear ventas" : map_ventas,
    "normalizar asistencia" : norm_asistencia,
    "limpiar precio": limpiar_precio,
    "rellenar nulos con 0": fillnull,
    "codificar sucursal": codificar_portales
}