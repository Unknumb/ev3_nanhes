from __future__ import annotations

import os
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL no esta definida. Configurala en tu entorno o en docker-compose."
        )
    return url


def preparar_tabla_nhanes(df: pd.DataFrame) -> pd.DataFrame:
    """Copia el dataframe procesado y normaliza nombres de columnas para SQL."""
    if df is None or df.empty:
        raise ValueError("El dataframe procesado esta vacio; no se puede cargar a BD.")

    out = df.copy()
    out.columns = [str(col).strip().lower() for col in out.columns]
    return out


def cargar_dataset_postgres(
    df: pd.DataFrame,
    table_name: str = "nhanes_processed",
    if_exists: str = "replace",
    schema: str | None = None,
) -> dict[str, Any]:
    """Escribe el dataframe procesado en Postgres usando SQLAlchemy."""
    engine = create_engine(_database_url())

    with engine.begin() as conn:
        df.to_sql(
            name=table_name,
            con=conn,
            schema=schema,
            if_exists=if_exists,
            index=False,
            method="multi",
            chunksize=1000,
        )

        total_rows = conn.execute(text(f'SELECT COUNT(*) FROM {table_name}')).scalar_one()

    return {
        "table_name": table_name,
        "rows_loaded": int(total_rows),
        "columns_loaded": len(df.columns),
        "if_exists": if_exists,
        "schema": schema,
    }
