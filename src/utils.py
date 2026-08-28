from pathlib import Path

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

