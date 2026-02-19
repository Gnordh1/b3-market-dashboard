import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

load_dotenv()  # carrega as variáveis do .env

RAW_PATH       = "data/raw/all_stocks.csv"
PROCESSED_PATH = "data/processed/stocks_features.csv"

TABLE_RAW       = "stocks_raw"
TABLE_PROCESSED = "stocks_features"


def get_engine():
    host     = os.getenv("DB_HOST")
    port     = os.getenv("DB_PORT")
    name     = os.getenv("DB_NAME")
    user     = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"

    try:
        engine = create_engine(url)
        # Testa a conexão
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Conexão com o banco '{name}' estabelecida com sucesso!")
        return engine
    except Exception as e:
        logger.error(f"Erro ao conectar com o banco de dados: {e}")
        raise


def load_csv(path: str) -> pd.DataFrame:
    logger.info(f"Lendo arquivo: {path}")
    df = pd.read_csv(path, parse_dates=["date"])
    logger.info(f"{len(df)} registros carregados")
    return df


def load_to_db(df: pd.DataFrame, table_name: str, engine) -> None:

    try:
        logger.info(f"Carregando dados na tabela '{table_name}'...")
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists="replace",  # recria a tabela se já existir
            index=False,
            chunksize=500,        
            method="multi"        
        )
        logger.info(f"Tabela '{table_name}': {len(df)} registros inseridos com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao carregar dados na tabela '{table_name}': {e}")
        raise


def validate_load(table_name: str, engine) -> None:
    query = f"SELECT ticker, COUNT(*) as registros FROM {table_name} GROUP BY ticker ORDER BY ticker"
    with engine.connect() as conn:
        result = pd.read_sql(text(query), conn)
    logger.info(f"\nValidação da tabela '{table_name}':\n{result.to_string(index=False)}")


if __name__ == "__main__":
    logger.info("=== Iniciando carga no PostgreSQL ===\n")

    engine = get_engine()

    df_raw = load_csv(RAW_PATH)
    load_to_db(df_raw, TABLE_RAW, engine)
    validate_load(TABLE_RAW, engine)

    df_processed = load_csv(PROCESSED_PATH)
    load_to_db(df_processed, TABLE_PROCESSED, engine)
    validate_load(TABLE_PROCESSED, engine)

    logger.info("\n=== Carga finalizada com sucesso! ===")
    logger.info("Tabelas disponíveis no banco:")
    logger.info(f"  → {TABLE_RAW}: dados brutos do yfinance")
    logger.info(f"  → {TABLE_PROCESSED}: dados com features para análise e dashboard")