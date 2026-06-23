"""Pipeline combinado: un solo modelo entrenado con TODOS los ciclos del equipo.

Reúne el trabajo de los tres ciclos (2013-2014 de Nicolás, 2015-2016 de Álvaro y
2017-2018 de Juan) en un único dataset y entrena un único par de modelos
(clasificación + regresión) sobre el contrato rico de 23 features.
"""

from .pipeline import create_pipeline

__all__ = ["create_pipeline"]
