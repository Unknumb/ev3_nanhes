"""Nodos del pipeline de serving.

El modelo de producción de la v1 es el del ciclo 2015 (clasificación + regresión).
Como el preprocesamiento vive DENTRO del Pipeline sklearn, cada pickle es
autocontenido: la API solo necesita pasarle el dict de features crudas.

Este nodo "bendice" los modelos versionados más recientes copiándolos a una ruta
estable (data/09_serving/) y emite un metadata.json con el contrato real
(feature_names_in_) leído del propio modelo entrenado, para que back y front
nunca se desincronicen del modelo servido.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def bendecir_modelos_serving(
    modelo_clasificacion: Any,
    modelo_regresion: Any,
) -> tuple[Any, Any, dict]:
    """Persiste los modelos 2015 a la ruta de serving y genera su metadata.

    Args:
        modelo_clasificacion: Pipeline sklearn (prep + XGBClassifier) entrenado.
        modelo_regresion: Pipeline sklearn (prep + XGBRegressor) entrenado.

    Returns:
        (clasificador, regresor, metadata) — el catálogo los escribe en
        data/09_serving/. Los modelos se devuelven sin modificar.
    """
    # feature_names_in_ lo fija el ColumnTransformer al ajustarse con un DataFrame:
    # es el contrato REAL de entrada del modelo (23 columnas NHANES).
    prep = modelo_clasificacion.named_steps["prep"]
    feature_cols = list(getattr(prep, "feature_names_in_", []))

    metadata = {
        "cycle": "2015-2016",
        "target_classification": "IS_LONGEVO",
        "target_regression": "RIDAGEYR",
        "n_features": len(feature_cols),
        "features": feature_cols,
        "classifier": type(modelo_clasificacion.named_steps["model"]).__name__,
        "regressor": type(modelo_regresion.named_steps["model"]).__name__,
        "blessed_at": datetime.now(timezone.utc).isoformat(),
    }
    print(
        f"Modelos 2015 bendecidos para serving "
        f"({metadata['n_features']} features): {feature_cols}"
    )
    return modelo_clasificacion, modelo_regresion, metadata
