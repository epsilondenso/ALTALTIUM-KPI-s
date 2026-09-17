from pathlib import Path
import pandas as pd
from src.utils import get_files
from config.config import columnas_archivo_citas 
from config.config import codif_sucursales
from src.utils import strip_df


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

def get_df(object: str|Path|pd.DataFrame, start: int = 2, stop: int = 4) -> pd.DataFrame:
    """
    Obtiene un DataFrame desde un archivo, directorio o instancia existente.

    Parameters
    ----------
    object : str | Path | pd.DataFrame
        Fuente de datos a cargar o retornar.
    start : int, optional
        Índice inicial al concatenar archivos de un directorio.
    stop : int, optional
        Índice final al concatenar archivos de un directorio.

    Returns
    -------
    pd.DataFrame
        DataFrame obtenido desde la fuente indicada.
    """

    if isinstance(object, Path):
        return concat_tables(dir = object, start = start, stop = stop)

    elif isinstance(object, str):
        return pd.read_excel(object)

    else:
        return object

def load_citas_df(citas_path: str):
    """
    Carga y limpia el archivo de citas.

    Parameters
    ----------
    citas_path : str
        Ruta del archivo CSV de citas.

    Returns
    -------
    pd.DataFrame
        DataFrame de citas con campos de texto normalizados.
    """
    citas = pd.read_csv(citas_path, 
                    delimiter= ";", 
                    header = 1, 
                    usecols = ["N"] + columnas_archivo_citas,
                    names = ["N"]+columnas_archivo_citas).dropna(subset = ["N"]+columnas_archivo_citas[:-1]).iloc[:, 1:]
    strip_df(citas)

    citas["ASISTENCIA"] = (
        citas["ASISTENCIA"]
        .str.lower()
        .str.replace(" ", "", regex=False)
        .str.replace(r"o$", "a", regex=True)
    )
    citas["VENTAS"] = citas["VENTAS"].fillna(0, inplace = False).apply(lambda x: 1.0 if not isinstance(x, int) else x)

    return citas

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