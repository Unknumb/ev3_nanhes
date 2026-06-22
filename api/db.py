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
    String,
    cast,
    create_engine,
    func,
    inspect,
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
    # Identificacion debil por correo (sin login). Solo se guarda el email si el
    # usuario dio consentimiento explicito (consent_save); ver save_prediction.
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    consent_save: Mapped[bool] = mapped_column(Boolean, default=False)


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


# Columnas agregadas despues de la v1 de la tabla. Migracion ligera (sin Alembic):
# si la tabla ya existe sin estas columnas, se añaden con ALTER TABLE best-effort.
_COLUMNAS_NUEVAS = {
    "email": "VARCHAR(254)",
    "consent_save": "BOOLEAN DEFAULT FALSE",
}


def _migrate_columns(engine) -> None:
    """ALTER TABLE ADD COLUMN para columnas nuevas si faltan (idempotente).

    create_all NO altera tablas existentes: si una BD vieja ya tiene `predictions`
    sin `email`/`consent_save`, las agregamos sin perder datos. Best-effort.
    """
    inspector = inspect(engine)
    if "predictions" not in inspector.get_table_names():
        return
    existentes = {c["name"] for c in inspector.get_columns("predictions")}
    faltantes = {k: v for k, v in _COLUMNAS_NUEVAS.items() if k not in existentes}
    if not faltantes:
        return
    with engine.begin() as conn:
        for nombre, tipo in faltantes.items():
            try:
                conn.execute(
                    text(f"ALTER TABLE predictions ADD COLUMN {nombre} {tipo}")
                )
            except Exception as exc:  # pragma: no cover - dialecto/carrera
                logger.warning("No se pudo añadir la columna %s: %s", nombre, exc)


@lru_cache(maxsize=1)
def _ensure_tables() -> None:
    """Crea las tablas una sola vez (idempotente). Independiente del lifespan.

    lru_cache solo memoiza retornos exitosos: si la BD esta caida y create_all
    lanza, no se cachea y se reintenta en la proxima llamada.
    """
    engine = get_engine()
    Base.metadata.create_all(engine)
    _migrate_columns(engine)


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


def save_prediction(
    result: dict[str, Any],
    features: dict[str, Any],
    email: str | None = None,
    consent_save: bool = False,
) -> bool:
    """Persiste una prediccion. Best-effort: nunca lanza, devuelve si tuvo exito.

    El `email` solo se guarda si `consent_save` es True (el usuario marco "guardar
    mi historial"). Sin consentimiento la fila queda anonima: cuenta para los
    agregados del dashboard pero no es recuperable por correo.
    """
    guardar_email = email if (consent_save and email) else None
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
                    email=guardar_email,
                    consent_save=bool(consent_save and email),
                )
            )
            session.commit()
        return True
    except Exception as exc:
        logger.warning("No se pudo guardar la prediccion: %s", exc)
        return False


def get_history(email: str, limit: int = 50) -> list[dict]:
    """Historial de un correo. Solo filas con consent_save=True (privacidad)."""
    _ensure_tables()
    with Session(get_engine()) as session:
        filas = list(
            session.scalars(
                select(Prediction)
                .where(Prediction.email == email)
                .where(Prediction.consent_save.is_(True))
                .order_by(Prediction.created_at.desc())
                .limit(limit)
            ).all()
        )
    return [
        {
            "created_at": r.created_at.isoformat(),
            "es_longevo": r.es_longevo,
            "probabilidad": r.probabilidad,
            "edad_biologica": r.edad_biologica,
            "edad_cronologica": r.edad_cronologica,
            "gap": r.gap,
            "features": r.features,
        }
        for r in filas
    ]


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
