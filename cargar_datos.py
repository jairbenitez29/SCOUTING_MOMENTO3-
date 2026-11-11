"""
Carga el dataset de Transfermarkt (players) en MySQL.

Uso (desde la carpeta del proyecto):
    python cargar_datos.py data/players_transfermarkt.zip
    python cargar_datos.py data/players.csv

Si no le pasas ruta, busca automáticamente un .zip o .csv dentro de la carpeta data/.
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd
from sqlalchemy import URL, create_engine, text

from src.database.connection2 import MySQLConnector

RAIZ = Path(__file__).resolve().parent
COLUMNAS_NECESARIAS = ["player_id", "name", "position", "height_in_cm",
                       "date_of_birth", "market_value_in_eur"]


def buscar_archivo():
    carpeta = RAIZ / "data"
    candidatos = sorted(carpeta.glob("*.zip")) + sorted(carpeta.glob("*.csv")) + sorted(carpeta.glob("*.sql"))
    if not candidatos:
        sys.exit("[ERROR] No encontré ningún .zip, .csv ni .sql en la carpeta data/. "
                 "Copia ahí el archivo players_transfermarkt.zip.")
    return candidatos[0]


def leer_csv(origen, nombre_interno=None):
    """Lee el CSV probando UTF-8 y, si falla, Latin-1."""
    for enc in ("utf-8", "latin-1"):
        try:
            if nombre_interno:
                with zipfile.ZipFile(origen) as z, z.open(nombre_interno) as f:
                    return pd.read_csv(f, encoding=enc, low_memory=False)
            return pd.read_csv(origen, encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    sys.exit("[ERROR] No pude leer el CSV (problema de codificación).")


def instrucciones_sql(ruta_sql, db):
    print("\n[INFO] El archivo es un volcado .sql. Impórtalo con UNA de estas opciones:")
    print("  a) MySQL Workbench: File > Run SQL Script... > elige el archivo > Run.")
    print("  b) phpMyAdmin (XAMPP): selecciona la base > pestaña Importar > elige el archivo > Continuar.")
    print(f"  c) Terminal:  mysql -u root -p {db} < \"{ruta_sql}\"")
    print("Luego corre:  python probar_conexion.py")


def main():
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else buscar_archivo()
    if not ruta.exists():
        sys.exit(f"[ERROR] No existe el archivo: {ruta}")
    print(f"[1/4] Archivo de datos: {ruta.name}")

    conector = MySQLConnector()
    db = conector.database

    # --- Leer el archivo (zip, csv o sql) ---
    if ruta.suffix.lower() == ".zip":
        with zipfile.ZipFile(ruta) as z:
            contenido = [n for n in z.namelist() if not n.endswith("/") and "__MACOSX" not in n]
        print(f"      Contenido del zip: {contenido}")
        csvs = [n for n in contenido if n.lower().endswith(".csv")]
        sqls = [n for n in contenido if n.lower().endswith(".sql")]
        if csvs:
            elegido = next((n for n in csvs if Path(n).stem.lower() == "players"), None) \
                or next((n for n in csvs if "player" in n.lower()), csvs[0])
            print(f"      Usando: {elegido}")
            df = leer_csv(ruta, elegido)
        elif sqls:
            destino = RAIZ / "data"
            with zipfile.ZipFile(ruta) as z:
                z.extract(sqls[0], destino)
            instrucciones_sql(destino / sqls[0], db)
            return
        else:
            sys.exit("[ERROR] El zip no trae ningún .csv ni .sql. Revisa qué contiene.")
    elif ruta.suffix.lower() == ".csv":
        df = leer_csv(ruta)
    elif ruta.suffix.lower() == ".sql":
        instrucciones_sql(ruta, db)
        return
    else:
        sys.exit("[ERROR] Formato no soportado. Usa .zip, .csv o .sql")

    print(f"      Filas leídas: {len(df):,} | Columnas: {len(df.columns)}")

    faltantes = [c for c in COLUMNAS_NECESARIAS if c not in df.columns]
    if faltantes:
        print(f"[ADVERTENCIA] Al CSV le faltan columnas que usa el examen: {faltantes}")
        print(f"              Columnas disponibles: {list(df.columns)}")

    # --- Tipos correctos para que la consulta del examen funcione ---
    for col in df.columns:
        if "date" in col.lower():
            df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in ["height_in_cm", "market_value_in_eur", "highest_market_value_in_eur"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # --- Crear la base de datos si no existe ---
    print(f"[2/4] Creando la base de datos '{db}' (si no existe)...")
    url_servidor = URL.create("mysql+pymysql", username=conector.user, password=conector.password,
                              host=conector.host, port=conector.port, query={"charset": "utf8mb4"})
    servidor = create_engine(url_servidor)
    try:
        with servidor.begin() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db}` "
                              "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
    except Exception as e:
        sys.exit(f"[ERROR] No pude conectarme a MySQL. Revisa usuario/contraseña en .env y que "
                 f"MySQL esté encendido.\n        Detalle: {e}")

    # --- Cargar la tabla ---
    print("[3/4] Cargando la tabla 'players' (puede tardar 1-2 minutos)...")
    df.to_sql("players", conector.engine, if_exists="replace", index=False,
              chunksize=2000, method="multi")
    if "player_id" in df.columns and df["player_id"].is_unique:
        with conector.engine.begin() as conn:
            conn.execute(text("ALTER TABLE players ADD PRIMARY KEY (player_id)"))

    # --- Verificación ---
    print("[4/4] Verificando...")
    total = conector.extract_data("SELECT COUNT(*) AS n FROM players")["n"].iloc[0]
    utiles = conector.extract_data(
        "SELECT COUNT(*) AS n FROM players "
        "WHERE market_value_in_eur IS NOT NULL AND date_of_birth IS NOT NULL"
    )["n"].iloc[0]
    print(f"\n[LISTO] Tabla players cargada en '{db}': {total:,} jugadores "
          f"({utiles:,} con valor de mercado y fecha de nacimiento).")
    print("Siguiente paso:  python probar_conexion.py")


if __name__ == "__main__":
    main()
