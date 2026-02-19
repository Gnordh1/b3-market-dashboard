import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


TICKERS = [
    "PETR4.SA",  # Petrobras
    "VALE3.SA",  # Vale
    "ITUB4.SA",  # Itaú Unibanco
    "BBDC4.SA",  # Bradesco
    "WEGE3.SA",  # WEG
    "MGLU3.SA",  # Magazine Luiza
    "ABEV3.SA",  # Ambev
    "BBAS3.SA",  # Banco do Brasil
]

END_DATE = datetime.today().strftime("%Y-%m-%d")
START_DATE = (datetime.today() - timedelta(days=365 * 2)).strftime("%Y-%m-%d")

OUTPUT_DIR = "data/raw"

def create_output_dir(path: str) -> None:
    """Cria o diretório de saída se não existir."""
    os.makedirs(path, exist_ok=True)
    logger.info(f"Diretório de saída: '{path}'")


def fetch_stock_data(ticker: str, start: str, end: str) -> pd.DataFrame | None:
    """
    Busca dados históricos de um ticker via yfinance.

    Retorna um DataFrame com colunas padronizadas ou None em caso de erro.
    """
    try:
        logger.info(f"Coletando dados de {ticker}...")
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)

        if df.empty:
            logger.warning(f"Nenhum dado retornado para {ticker}. Verifique o ticker.")
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.columns = [col.lower().replace(" ", "_") for col in df.columns]

        df["ticker"] = ticker
        df = df.reset_index().rename(columns={"Date": "date", "index": "date"})
        df["date"] = pd.to_datetime(df["date"])

        cols = ["date", "ticker", "open", "high", "low", "close", "volume"]
        df = df[[c for c in cols if c in df.columns]]

        logger.info(f"{ticker}: {len(df)} registros coletados ({start} → {end})")
        return df

    except Exception as e:
        logger.error(f"Erro ao coletar {ticker}: {e}")
        return None


def save_to_csv(df: pd.DataFrame, ticker: str, output_dir: str) -> None:
    """Salva o DataFrame como CSV na pasta de dados brutos."""
    filename = ticker.replace(".SA", "").lower()
    filepath = os.path.join(output_dir, f"{filename}.csv")
    df.to_csv(filepath, index=False)
    logger.info(f"Salvo em: {filepath}")


def collect_all(tickers: list, start: str, end: str, output_dir: str) -> pd.DataFrame:

    all_data = []

    for ticker in tickers:
        df = fetch_stock_data(ticker, start, end)
        if df is not None:
            save_to_csv(df, ticker, output_dir)
            all_data.append(df)

    if not all_data:
        logger.error("Nenhum dado foi coletado. Verifique sua conexão e os tickers.")
        return pd.DataFrame()

    consolidated = pd.concat(all_data, ignore_index=True)
    consolidated_path = os.path.join(output_dir, "all_stocks.csv")
    consolidated.to_csv(consolidated_path, index=False)
    logger.info(f"Total de registros: {len(consolidated)}")

    return consolidated

if __name__ == "__main__":
    logger.info(f"Período: {START_DATE} → {END_DATE}")
    logger.info(f"Tickers: {TICKERS}\n")

    create_output_dir(OUTPUT_DIR)
    df = collect_all(TICKERS, START_DATE, END_DATE, OUTPUT_DIR)

    if not df.empty:
        logger.info("\n=== Coleta finalizada com sucesso! ===")
        logger.info(f"\nAmostra dos dados:\n{df.head(10).to_string(index=False)}")
    else:
        logger.error("Coleta finalizada com erros.")