import pandas as pd
from pathlib import Path
import yaml
from src.utils import strip_df
from src.preprocessing import transformations

#No se usa
def convert_boolean(
    series: pd.Series,
    true_values: list[str],
    false_values: list[str]
) -> pd.Series:

    true_values = {str(x).strip().lower() for x in true_values}
    false_values = {str(x).strip().lower() for x in false_values}

    values = series.astype("string").str.strip().str.lower()

    result = pd.Series(pd.NA, index=series.index, dtype="boolean")

    result[values.isin(true_values)] = True
    result[values.isin(false_values)] = False

    # Detectar valores que no conocemos
    unknown = values.notna() & ~values.isin(
        true_values | false_values
    )

    if unknown.any():
        raise ValueError(
            f"Valores booleanos desconocidos en '{series.name}': "
            f"{series[unknown].unique().tolist()}"
        )

    return result

#Función que aplica transformaciones a una columna
def apply_column_transformations(
    series: pd.Series,
    transforms: list[str]
) -> pd.Series:

    for transformation in transforms:

        if transformation not in transformations:
            raise ValueError(
                f"Transformación desconocida: {transformation}"
            )

        function = transformations[transformation]

        series = function(series)

    return series

def load_table(
    path: str|Path, 
    yaml_path: str
) -> pd.DataFrame | None:
    """
    Selecciona, renombra y convierte las columnas de un DataFrame
    según la configuración definida en un archivo YAML.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame original.

    yaml_path : str
        Ruta al archivo YAML que define la tabla.

    Returns
    -------
    pd.DataFrame
        DataFrame limpio con únicamente las columnas indicadas
        por el YAML.
    """
    # Leer YAML
    with open(yaml_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    #Obtener extensión del archivo
    extension = Path(path).suffix

    #Leer archivo
    if extension == ".csv":
        df = pd.read_csv(path, encoding="utf-8", **config["read_csv"])
    
    elif extension == ".xlsx":
        df = pd.read_excel(path, engine = "openpyxl")

    else:
        raise ValueError("Valid extensions are .csv and .xlsx")
        return None
    
    #Preprocesamiento simple
    if config["strip"]:
        strip_df(df, inplace=True)

    columns = config["columns"]

    # Solo columnas que se conservarán
    columns_to_keep = [
        column for column in columns
        if column["keep"]
    ]

    # Verificar que todas las columnas existan
    missing_columns = [
        column["source"]
        for column in columns_to_keep
        if column["source"] not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Faltan columnas en el DataFrame: {missing_columns}"
        )

    # Seleccionar columnas originales
    result = df[
        [column["source"] for column in columns_to_keep]
    ].copy()

    # Renombrar
    rename_map = {
        column["source"]: column["name"]
        for column in columns_to_keep
    }

    result = result.rename(columns=rename_map)

    # Convertir tipos, tratar nulos y aplicar transformaciones por columna
    for column in columns_to_keep:
        #Tratar nulos
        if "dropna" in column and column["dropna"]:
            result.dropna(subset = column["name"], inplace = True)

        if "fillna" in column:
            result[name] = result[name].fillna(column["fillna"])

        #Convertir tipos
        name = column["name"]
        dtype = column["pandas_dtype"]

        if dtype == "datetime64[ns]":
            result[name] = pd.to_datetime(
            result[name],
            errors="coerce",
            dayfirst=True
        )

        elif dtype == "boolean":
            result[name] = result[name].apply(lambda x: True if x in column["true_values"] else False)

        elif dtype.lower() in ["int64", "float64"]:
            result[name] = pd.to_numeric(result[name], errors= "coerce").astype(dtype)

        else:
            result[name] = result[name].astype(dtype)

        #Aplicar transformaciones
        if "transformations" in column:
            transforms = column.get(
                "transformations",
                []
            )
            result[name] = apply_column_transformations(series = result[name], 
                                                        transforms= transforms)

    return result