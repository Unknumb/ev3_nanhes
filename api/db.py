"""Capa de persistencia: historial de predicciones en SQL.

Tercera fuente de datos del proyecto (junto a los archivos NHANES y la API REST):
una base **SQL** que guarda cada prediccion servida. El dashboard ejecutivo lee de
aqui los agregados (distribucion de edad biologica, % longevos, etc.).

- Configurable por entorno con `DATABASE_URL` (Postgres en prod via docker-compose,
  SQLite como fallback de desarrollo local).
- La escritura es **best-effort**: si la BD no esta disponible, la API igual responde
  la prediccion; nunca tumba `/predict`.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Integer,
    cast,
    create_engine,
    func,
    select,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

logger = logging.getLogger("ev3.api.db")

# Raiz del repo (misma convencion que model_registry) para el sqlite por defecto.
_ROOT = Path(os.getenv("EV3_ROOT", Path(__file__).resolve().parent.parent))
_DEFAULT_SQLITE = f"sqlite:///{_ROOT / 'data' / 'predictions.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", _DEFAULT_SQLITE)


class Base(DeclarativeBase):
    pass


class Prediction(Base):
    """Una fila por prediccion servida por la API."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    es_longevo: Mapped[bool] = mapped_column(Boolean)
    probabilidad: Mapped[float] = mapped_column(Float)
    edad_biologica: Mapped[float] = mapped_column(Float)
    edad_cronologica: Mapped[float | None] = mapped_column(Float, nullable=True)
    gap: Mapped[float | None] = mapped_column(Float, nullable=True)
    features: Mapped[dict] = mapped_column(JSON)  # dict crudo de entrada (JSON/JSONB)


@lru_cache(maxsize=1)
def get_engine():
    """Engine perezoso (memoizado). Crea la carpeta del sqlite local si hace falta."""
    connect_args = (
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    )
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = DATABASE_URL.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(DATABASE_URL, connect_args=connect_args, future=True)


@lru_cache(maxsize=1)
def _ensure_tables() -> None:
    """Crea las tablas una sola vez (idempotente). Independiente del lifespan.

    lru_cache solo memoiza retornos exitosos: si la BD esta caida y create_all
    lanza, no se cachea y se reintenta en la proxima llamada.
    """
    Base.metadata.create_all(get_engine())


def init_db() -> bool:
    """Inicializa la BD al arranque. Best-effort: False si la BD no responde."""
    try:
        _ensure_tables()
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("No se pudo inicializar la BD (%s): %s", DATABASE_URL, exc)
        return False


def db_ready() -> bool:
    """True si la BD acepta conexiones (para /health)."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def save_prediction(result: dict[str, Any], features: dict[str, Any]) -> bool:
    """Persiste una prediccion. Best-effort: nunca lanza, devuelve si tuvo exito."""
    try:
        _ensure_tables()
        with Session(get_engine()) as session:
            session.add(
                Prediction(
                    es_longevo=bool(result["es_longevo"]),
                    probabilidad=float(result["probabilidad"]),
                    edad_biologica=float(result["edad_biologica"]),
                    edad_cronologica=result.get("edad_cronologica"),
                    gap=result.get("gap"),
                    features=dict(features),
                )
            )
            session.commit()
        return True
    except Exception as exc:
        logger.warning("No se pudo guardar la prediccion: %s", exc)
        return False


def get_aggregates(hist_bins: int = 10) -> dict:
    """Agregados para el dashboard ejecutivo (lee del historial).

    Devuelve totales, % de longevos, edad biologica promedio, gap promedio, un
    histograma de edad biologica y las ultimas predicciones.
    """
    _ensure_tables()
    with Session(get_engine()) as session:
        total = session.scalar(select(func.count(Prediction.id))) or 0
        if total == 0:
            return {
                "total_predicciones": 0,
                "pct_longevos": None,
                "edad_biologica_promedio": None,
                "gap_promedio": None,
                "edad_biologica_distribucion": [],
                "ultimas": [],
            }
        pct_longevos = session.scalar(
            select(func.avg(cast(Prediction.es_longevo, Integer)))
        )
        edad_prom = session.scalar(select(func.avg(Prediction.edad_biologica)))
        gap_prom = session.scalar(select(func.avg(Prediction.gap)))
        edades = list(session.scalars(select(Prediction.edad_biologica)).all())
        ultimas_rows = list(
            session.scalars(
                select(Prediction).order_by(Prediction.created_at.desc()).limit(10)
            ).all()
        )

    counts, edges = np.histogram(np.asarray(edades, dtype=float), bins=hist_bins)
    distribucion = [
        {
            "min": round(float(edges[i]), 1),
            "max": round(float(edges[i + 1]), 1),
            "count": int(counts[i]),
        }
        for i in range(len(counts))
    ]
    ultimas = [
        {
            "created_at": r.created_at.isoformat(),
            "es_longevo": r.es_longevo,
            "probabilidad": r.probabilidad,
            "edad_biologica": r.edad_biologica,
            "gap": r.gap,
        }
        for r in ultimas_rows
    ]
    return {
        "total_predicciones": int(total),
        "pct_longevos": (
            round(float(pct_longevos) * 100, 1) if pct_longevos is not None else None
        ),
        "edad_biologica_promedio": (
            round(float(edad_prom), 1) if edad_prom is not None else None
        ),
        "gap_promedio": round(float(gap_prom), 1) if gap_prom is not None else None,
        "edad_biologica_distribucion": distribucion,
        "ultimas": ultimas,
    }
