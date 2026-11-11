"""Lectura de datos consistente desde MySQL o el CSV original."""
from pathlib import Path
import zipfile
import pandas as pd
from src.database.connection2 import MySQLConnector

FECHA_REFERENCIA = "2026-10-07"  # Fecha del informe original, fija para reproducibilidad.


def obtener_datos(origen="mysql"):
    if origen == "mysql":
        consulta = f"""SELECT player_id, name AS jugador, position AS posicion,
          height_in_cm AS estatura_cm,
          TIMESTAMPDIFF(YEAR, date_of_birth, '{FECHA_REFERENCIA}') AS edad,
          market_value_in_eur AS valor_mercado
          FROM players WHERE market_value_in_eur IS NOT NULL
          AND date_of_birth IS NOT NULL
          AND date_of_birth <= '{FECHA_REFERENCIA}'"""
        df = MySQLConnector().extract_data(consulta)
        if df.empty:
            raise RuntimeError("MySQL no devolvió registros. Configura .env, importa los datos y vuelve a ejecutar; o usa --origen csv.")
        return df
    if origen != "csv":
        raise ValueError("Origen debe ser 'mysql' o 'csv'")
    ruta = Path(__file__).resolve().parents[1] / "data" / "players_transfermarkt.zip"
    with zipfile.ZipFile(ruta) as z:
        with z.open('players.csv') as f:
            df = pd.read_csv(f, usecols=['player_id','name','position','height_in_cm','date_of_birth','market_value_in_eur'])
    df['date_of_birth'] = pd.to_datetime(df['date_of_birth'], errors='coerce')
    referencia = pd.Timestamp(FECHA_REFERENCIA)
    df = df[df['market_value_in_eur'].notna() & df['date_of_birth'].notna() & (df['date_of_birth'] <= referencia)].copy()
    df['edad'] = referencia.year - df['date_of_birth'].dt.year - (
       (referencia.month < df['date_of_birth'].dt.month) |
       ((referencia.month == df['date_of_birth'].dt.month) & (referencia.day < df['date_of_birth'].dt.day))
    ).astype(int)
    return df.rename(columns={'name':'jugador','position':'posicion','height_in_cm':'estatura_cm','market_value_in_eur':'valor_mercado'})[
        ['player_id','jugador','posicion','estatura_cm','edad','valor_mercado']]
