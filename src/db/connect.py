import psycopg2
import streamlit as st
def get_connection(host: str = "localhost",
                  port: int = 5432, 
                  dbname: str = "kpis_altaltium",
                  user: str = "postgres",
                  password: str = "aVs#1105"):

    if "connections" in st.secrets:
        return psycopg2.connect(
            st.secrets["connections"]["neon"]["url"]
        )
    
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="kpis_altaltium",
        user="postgres",
        password="aVs#1105"
    )

    return conn