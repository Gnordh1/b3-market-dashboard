import pandas as pd
from prophet import Prophet
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import logging
import warnings

warnings.filterwarnings("ignore")  

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)
logging.getLogger("prophet").setLevel(logging.WARNING)
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)


load_dotenv()

FORECAST_DAYS  = 30       
TABLE_INPUT    = "stocks_features"
TABLE_OUTPUT   = "stocks_forecast"
OUTPUT_CSV     = "data/processed/stocks_forecast.csv"


def get_engine():
    url = (
        f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    engine = create_engine(url)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("Conexão com o banco estabelecida!")
    return engine


def load_features(engine) -> pd.DataFrame:
    query = f"SELECT date, ticker, close FROM {TABLE_INPUT} ORDER BY ticker, date"
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, parse_dates=["date"])
    logger.info(f"{len(df)} registros carregados | {df['ticker'].nunique()} tickers")
    return df


def train_and_forecast(df_ticker: pd.DataFrame, ticker: str) -> pd.DataFrame:
    df_prophet = df_ticker[["date", "close"]].rename(columns={"date": "ds", "close": "y"})

    model = Prophet(
        changepoint_prior_scale=0.05,
        seasonality_mode="multiplicative",
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False
    )

    model.fit(df_prophet)

    future = model.make_future_dataframe(periods=FORECAST_DAYS, freq="B")  # "B" = business days
    forecast = model.predict(future)

    result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    result.columns = ["date", "predicted_close", "lower_bound", "upper_bound"]
    result["ticker"] = ticker

    last_date = df_ticker["date"].max()
    result["is_forecast"] = result["date"] > last_date

    logger.info(f"{ticker}: previsão gerada para os próximos {FORECAST_DAYS} dias úteis")
    return result


def forecast_all(df: pd.DataFrame) -> pd.DataFrame:
    all_forecasts = []
    tickers = df["ticker"].unique()

    for ticker in tickers:
        df_ticker = df[df["ticker"] == ticker].copy()
        forecast = train_and_forecast(df_ticker, ticker)
        all_forecasts.append(forecast)

    return pd.concat(all_forecasts, ignore_index=True)


def save_forecast(df: pd.DataFrame, engine) -> None:
    df.to_sql(
        name=TABLE_OUTPUT,
        con=engine,
        if_exists="replace",
        index=False,
        chunksize=500,
        method="multi"
    )
    logger.info(f"Tabela '{TABLE_OUTPUT}': {len(df)} registros inseridos no banco")

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    logger.info(f"Previsões salvas em: {OUTPUT_CSV}")


def show_summary(df: pd.DataFrame) -> None:
    forecasts_only = df[df["is_forecast"]].copy()
    logger.info("\n=== Resumo das Previsões (próximos 30 dias) ===")
    for ticker in forecasts_only["ticker"].unique():
        df_t = forecasts_only[forecasts_only["ticker"] == ticker]
        last_pred = df_t.iloc[-1]
        logger.info(
            f"{ticker}: previsão final = R$ {last_pred['predicted_close']:.2f} "
            f"(intervalo: {last_pred['lower_bound']:.2f} ~ {last_pred['upper_bound']:.2f})"
        )


if __name__ == "__main__":

    engine = get_engine()
    df = load_features(engine)

    logger.info(f"\nTreinando modelos para {df['ticker'].nunique()} tickers...")
    df_forecast = forecast_all(df)

    save_forecast(df_forecast, engine)
    show_summary(df_forecast)

    logger.info("\n=== Previsões finalizadas com sucesso! ===")
