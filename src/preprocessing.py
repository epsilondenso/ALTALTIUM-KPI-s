from pathlib import Path
import pandas as pd
from src.utils import get_files

def concat_tables(dir: str|Path, 
                       start: int = 2,
                       stop: int = 4,
                       output: str|Path|None = "concat_path.csv",
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