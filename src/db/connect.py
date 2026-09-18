import psycopg2
import streamlit as st

def get_connection(
    host: str = "localhost",
    port: int = 5432,
    dbname: str = "kpis_altaltium",
    user: str = "postgres",
    password: str = "TU_PASSWORD"
):
    if "DB_URL" in st.secrets:
        return psycopg2.connect(st.secrets["DB_URL"])

    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password
    )