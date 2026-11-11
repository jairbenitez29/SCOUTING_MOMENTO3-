"""
Prueba rápida: ¿Python se conecta a MySQL y la consulta del examen devuelve datos?

Uso (desde la carpeta del proyecto):
    python probar_conexion.py
"""
from src.database.connection2 import MySQLConnector

QUERY_EXAMEN = """
    SELECT
        p.player_id,
        p.name AS jugador,
        p.position AS posicion,
        p.height_in_cm AS estatura_cm,
        TIMESTAMPDIFF(YEAR, p.date_of_birth, CURDATE()) AS edad,
        p.market_value_in_eur AS valor_mercado
    FROM players p
    WHERE p.market_value_in_eur IS NOT NULL
      AND p.date_of_birth IS NOT NULL;
"""


def main():
    db = MySQLConnector()
    print(f"Conectando a {db.user}@{db.host}:{db.port}/{db.database} ...")
    if not db.test_connection():
        print("\nRevisa: 1) que MySQL esté encendido, 2) usuario y contraseña en .env, "
              "3) que corriste antes  python cargar_datos.py")
        return
    print("[OK] Conexión exitosa.\n")

    df = db.extract_data(QUERY_EXAMEN)
    if df.empty:
        print("La consulta no devolvió datos. ¿Ya cargaste la tabla players?")
        return

    print(f"\nRegistros que usará el examen: {len(df):,}")
    print("\nPrimeras filas:")
    print(df.head().to_string(index=False))
    print("\nPosiciones:")
    print(df["posicion"].value_counts(dropna=False).to_string())
    print(f"\nEstaturas vacías (se imputan en el examen): {df['estatura_cm'].isna().sum():,}")
    print("\nTodo listo para correr:  python evaluacion_integral.py")


if __name__ == "__main__":
    main()
