import pandas as pd
import numpy as np
import os
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

INPUT_PATH  = "data/raw/all_stocks.csv"
OUTPUT_DIR  = "data/processed"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "stocks_features.csv")


def load_raw_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    logger.info(f"{len(df)} registros carregados | {df['ticker'].nunique()} tickers")
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    initial_len = len(df)
    df = df.drop_duplicates(subset=["date", "ticker"])
    df = df.dropna(subset=["open", "high", "low", "close", "volume"])
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    logger.info(f"Limpeza: {initial_len - len(df)} registros removidos | {len(df)} restantes")
    return df


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    for window in [7, 21, 30]:
        df[f"ma_{window}"] = (
            df.groupby("ticker")["close"]
            .transform(lambda x: x.rolling(window=window, min_periods=1).mean())
        )
    logger.info("Médias móveis calculadas: MA7, MA21, MA30")
    return df


def add_daily_return(df: pd.DataFrame) -> pd.DataFrame:
    df["daily_return"] = (
        df.groupby("ticker")["close"]
        .transform(lambda x: x.pct_change())
    )
    logger.info("Retorno diário calculado")
    return df


def add_cumulative_return(df: pd.DataFrame) -> pd.DataFrame:
    df["cumulative_return"] = (
        df.groupby("ticker")["daily_return"]
        .transform(lambda x: (1 + x).cumprod() - 1)
    )
    logger.info("Retorno acumulado calculado")
    return df


def add_volatility(df: pd.DataFrame, window: int = 21) -> pd.DataFrame:
    df[f"volatility_{window}d"] = (
        df.groupby("ticker")["daily_return"]
        .transform(lambda x: x.rolling(window=window, min_periods=1).std())
    )
    logger.info(f"Volatilidade ({window} dias) calculada")
    return df


def add_volume_ma(df: pd.DataFrame, window: int = 21) -> pd.DataFrame:
    df[f"volume_ma_{window}"] = (
        df.groupby("ticker")["volume"]
        .transform(lambda x: x.rolling(window=window, min_periods=1).mean())
    )
    df["volume_ratio"] = df["volume"] / df[f"volume_ma_{window}"]
    logger.info("Média móvel de volume e volume ratio calculados")
    return df


def add_price_range(df: pd.DataFrame) -> pd.DataFrame:
    df["price_range_pct"] = (df["high"] - df["low"]) / df["low"] * 100
    logger.info("Amplitude de preço diária calculada")
    return df


def save_processed(df: pd.DataFrame, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    logger.info(f"Dados processados salvos em: {path}")


if __name__ == "__main__":

    df = load_raw_data(INPUT_PATH)
    df = clean_data(df)
    df = add_moving_averages(df)
    df = add_daily_return(df)
    df = add_cumulative_return(df)
    df = add_volatility(df)
    df = add_volume_ma(df)
    df = add_price_range(df)

    save_processed(df, OUTPUT_PATH)

    logger.info("\n=== Transformação finalizada com sucesso! ===")
    logger.info(f"\nColunas geradas:\n{list(df.columns)}")
    logger.info(f"\nAmostra dos dados processados:\n{df.tail(5).to_string(index=False)}")