from pathlib import Path
import pandas as pd
from src.utils import get_files
from config.config import columnas_archivo_citas 
from src.utils import strip_df


def concat_tables(dir: str|Path, 
                       start: int = 2,
                       stop: int = 4,
                       output: str|Path|None = None,
                       return_concat: bool = True) -> pd.DataFrame|None :

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
    
    files = get_files(dir)
    tables = [pd.read_excel(dir /file) for file in files[start-1:stop]]
    concat = pd.concat(tables)

    if output is not None:
        concat.to_csv(path_or_buf= output, index= False)
    return concat if return_concat else None 

def get_df(object: str|Path|pd.DataFrame, start: int = 2, stop: int = 4) -> pd.DataFrame:

        if isinstance(object, Path):
            return concat_tables(dir = object, start = start, stop = stop)
        
        elif isinstance(object, str):
            return pd.read_excel(object)
        
        else:
            return object

def load_citas_df(citas_path: str):
    citas = pd.read_csv(citas_path, 
                    delimiter= ";", 
                    header = 1, 
                    usecols = ["N"] + columnas_archivo_citas,
                    names = ["N"]+columnas_archivo_citas).dropna(subset = ["N"]+columnas_archivo_citas[:-1]).iloc[:, 1:]
    strip_df(citas)
    citas["ASISTENCIA"] = [asis.lower().replace(" ", "") for asis in citas["ASISTENCIA"]]

    return citas

