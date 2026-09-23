from pathlib import Path
import pandas as pd

def get_files(dir: str|Path):

    """
    Obtiene los nombres de los archivos de un directorio.

    Parameters
    ----------
    dir : str | Path
        Directorio del que se obtendrán los archivos.

    Returns
    -------
    list[str]
        Lista con los nombres de los archivos encontrados.
    """

    files_list = [file.name for file in dir.iterdir() if file.is_file()] 
    return files_list

def strip_df(df: pd.DataFrame, inplace: bool = True):
    """
    Elimina espacios al inicio y final de columnas de texto.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame cuyos campos de texto se limpiarán.
    inplace : bool, optional
        Indica si se modifica el DataFrame original.

    Returns
    -------
    pd.DataFrame | None
        Copia limpia si `inplace` es False; de lo contrario, None.
    """
    
    cols = df.select_dtypes(include=["object", "string"]).columns

    if inplace:
        df[cols] = df[cols].apply(lambda col: col.str.strip())
        return None
    else:
        copy = df.copy()
        copy[cols] = copy[cols].apply(lambda col: col.str.strip())
        return copy
