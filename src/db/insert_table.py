import pandas as pd
import yaml
import psycopg2
from psycopg2.extras import execute_values

def insert_table(
    df: pd.DataFrame,
    yaml_path: str,
    connection
):
    with open(yaml_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    table_name = config["table"]
    primary_key = config.get("primary_key")

    columns = [
        column
        for column in config["columns"]
        if column["keep"]
    ]

    column_names = [column["name"] for column in columns]

    # --------------------------------------------------
    # PRIMARY KEY
    # --------------------------------------------------

    if primary_key and primary_key not in column_names:
        raise ValueError(
            f"La primary key '{primary_key}' no está "
            f"definida entre las columnas."
        )

    # --------------------------------------------------
    # CREATE TABLE
    # --------------------------------------------------

    definitions = ", ".join(
        f'"{column["name"]}" {column["sql_type"]}'
        for column in columns
    )

    if primary_key:
        definitions += f', PRIMARY KEY ("{primary_key}")'

    create_query = f"""
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            {definitions}
        );
    """

    # --------------------------------------------------
    # INSERT
    # --------------------------------------------------

    names = ", ".join(
        f'"{name}"'
        for name in column_names
    )

    insert_query = f"""
        INSERT INTO "{table_name}" ({names})
        VALUES %s
    """

    # Si hay primary key, hacemos UPSERT
    if primary_key:

        update_columns = ", ".join(
            f'"{name}" = EXCLUDED."{name}"'
            for name in column_names
            if name != primary_key
        )

        insert_query += f"""
            ON CONFLICT ("{primary_key}")
            DO UPDATE SET
                {update_columns};
        """

    else:
        insert_query += ";"

    # --------------------------------------------------
    # DATA
    # --------------------------------------------------

    data = (
        df[column_names]
        .astype(object)
        .where(pd.notna(df[column_names]), None)
        .itertuples(index=False, name=None)
    )

    cursor = connection.cursor()

    try:
        cursor.execute(create_query)

        execute_values(
            cursor,
            insert_query,
            data
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()