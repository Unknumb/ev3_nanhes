"""Modelos Pydantic de request/response + validacion contra feature_schema.json."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .model_registry import load_schema


class PredictRequest(BaseModel):
    """Entrada de prediccion.

    `features` mapea codigo NHANES -> valor (numerico o codigo de categoria).
    Los campos opcionales pueden omitirse o ir en null: el modelo los imputa.
    `edad_cronologica` NO es feature del modelo; solo sirve para el gap.
    """

    features: dict[str, float | int | None] = Field(default_factory=dict)
    edad_cronologica: float | None = None
    # Opcionales: el correo solo se persiste si `guardar` es True (consentimiento).
    email: str | None = None
    guardar: bool = False


class PredictResponse(BaseModel):
    es_longevo: bool
    probabilidad: float
    edad_biologica: float
    edad_cronologica: float | None = None
    gap: float | None = None


def validate_features(features: dict[str, float | int | None]) -> list[str]:
    """Valida required y rangos contra el schema. Devuelve lista de errores."""
    schema = load_schema()
    errores: list[str] = []
    spec_por_codigo = {f["code"]: f for f in schema["features"]}

    desconocidas = set(features) - set(spec_por_codigo)
    if desconocidas:
        errores.append(f"Features desconocidas: {sorted(desconocidas)}")

    for spec in schema["features"]:
        code = spec["code"]
        val = features.get(code)
        if val is None:
            if spec.get("required"):
                errores.append(f"'{code}' ({spec['label']}) es requerido")
            continue
        if spec["type"] == "numeric":
            lo, hi = spec.get("min"), spec.get("max")
            if lo is not None and val < lo or hi is not None and val > hi:
                errores.append(f"'{code}' fuera de rango [{lo}, {hi}]: {val}")
        elif spec["type"] == "categorical":
            validos = {o["value"] for o in spec["options"]}
            if val not in validos:
                errores.append(
                    f"'{code}' no es una categoria valida {sorted(validos)}: {val}"
                )
    return errores
