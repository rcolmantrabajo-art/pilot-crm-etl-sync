import os
import urllib.parse
import clickhouse_connect
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env local
load_dotenv()

INSTANCIA_MIN = os.getenv("INSTANCIA_MIN")
INSTANCIA_MAY = os.getenv("INSTANCIA_MAY")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS_RAW = os.getenv("DB_PASS")
DB_PASS = urllib.parse.quote_plus(DB_PASS_RAW) if DB_PASS_RAW else ""

CERT_PATH = os.getenv("CERT_PATH")
KEY_PATH = os.getenv("KEY_PATH")

TABLAS_PILOT = [
    "bi_ft_leads",
    "bi_ft_customer_care",
    "bi_ft_leads_scoring",
    "bi_ft_sales",
    "bi_ft_testdrives",
]


def ejecutar_etl():
  print("Iniciando proceso de sincronización con ClickHouse...")

  try:
    client = clickhouse_connect.get_client(
        host=f"{INSTANCIA_MIN}.bi.pilotcrm.io",
        port=8443,
        secure=True,
        username=f"usr_{INSTANCIA_MIN}",
        client_cert=CERT_PATH,
        client_cert_key=KEY_PATH,
        verify=False,
    )

    engine = create_engine(
        f"postgresql+pg8000://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
        client_encoding="utf8",
    )

    for tabla in TABLAS_PILOT:
      print(f"Procesando tabla: {tabla}")

      query = f"""
            SELECT *
            FROM {INSTANCIA_MAY}.{tabla}
            WHERE created_datetime >= now() - INTERVAL 30 DAY
            """

      result = client.query(query)
      df_data = pd.DataFrame(result.result_rows, columns=result.column_names)

      if df_data.empty:
        print(f"-> Advertencia: La tabla {tabla} no registra datos recientes.")
        continue

      df_data.columns = [str(col).lower() for col in df_data.columns]
      print(
          f"-> Registros descargados: {len(df_data)} | Columnas:"
          f" {len(df_data.columns)}"
      )

      with engine.begin() as conn:
        stg_table = f"stg_{tabla}"

        # Preparación del entorno de staging
        conn.execute(text(f"DROP TABLE IF EXISTS {stg_table};"))
        df_data.to_sql(stg_table, conn, if_exists="replace", index=False)

        # Creación de tabla destino si no existe
        conn.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {tabla} AS
                    SELECT * FROM {stg_table} WHERE 1=0;
                """))

        # Verificación y asignación de Primary Key
        conn.execute(text(f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint WHERE conname = '{tabla}_pkey'
                        ) THEN
                            ALTER TABLE {tabla} ADD PRIMARY KEY (id);
                        END IF;
                    END $$;
                """))

        # Ejecución de UPSERT sobre la tabla destino
        cols = [f'"{col}"' for col in df_data.columns]
        cols_str = ", ".join(cols)
        update_str = ", ".join(
            [f"{col} = EXCLUDED.{col}" for col in cols if col != '"id"']
        )

        upsert_query = text(f"""
                    INSERT INTO {tabla} ({cols_str})
                    SELECT {cols_str}
                    FROM {stg_table}
                    ON CONFLICT (id) DO UPDATE SET
                        {update_str};
                """)
        conn.execute(upsert_query)

        # Limpieza de staging
        conn.execute(text(f"DROP TABLE IF EXISTS {stg_table};"))

      print(f"-> OK: Tabla {tabla} sincronizada correctamente.")

    print("Proceso de sincronización finalizado con éxito.")

  except Exception as e:
    print(f"Error crítico durante la ejecución del ETL: {e}")


if __name__ == "__main__":
  ejecutar_etl()
