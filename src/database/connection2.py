"""
Conector a MySQL para el Momento 2 (Minería de Datos).

Lee los datos de conexión del archivo .env que está en la raíz del proyecto.
Si no existe .env, usa los valores por defecto de abajo.
"""
import os
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text

# Carga el archivo .env de la raíz del proyecto (si python-dotenv está instalado)
try:
    from dotenv import load_dotenv

    RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
    load_dotenv(RAIZ_PROYECTO / ".env")
except ImportError:
    pass


class MySQLConnector:
    def __init__(self, host=None, port=None, user=None, password=None, database=None):
        self.host = host or os.getenv("DB_HOST", "localhost")
        self.port = int(port or os.getenv("DB_PORT", "3306"))
        self.user = user or os.getenv("DB_USER", "root")
        self.password = password if password is not None else os.getenv("DB_PASSWORD", "")
        self.database = database or os.getenv("DB_NAME", "transfermarkt")

        url = (
            f"mysql+pymysql://{self.user}:{quote_plus(self.password)}"
            f"@{self.host}:{self.port}/{self.database}?charset=utf8mb4"
        )
        self.engine = create_engine(url, pool_pre_ping=True)

    def extract_data(self, query):
        """Ejecuta un SELECT y devuelve un DataFrame. Si falla, devuelve un DataFrame vacío."""
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(text(query.strip().rstrip(";")), conn)
            print(f"[OK] Consulta ejecutada. Filas obtenidas: {len(df)}")
            return df
        except Exception as e:
            print(f"[ERROR] No se pudo consultar MySQL: {e}")
            return pd.DataFrame()

    def test_connection(self):
        """Devuelve True si se puede conectar a la base de datos."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"[ERROR] Conexión fallida: {e}")
            return False
