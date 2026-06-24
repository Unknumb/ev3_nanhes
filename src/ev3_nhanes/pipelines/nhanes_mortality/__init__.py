"""MVP: predicción de mortalidad a 10 años (modelo de supervivencia, binario).

Distinto del modelo de edad biológica: el target es la mortalidad observada en el
seguimiento (NHANES Linked Mortality Files), no la edad actual. Ver
docs/prediccion_mortalidad.md.
"""

from .pipeline import create_pipeline

__all__ = ["create_pipeline"]
