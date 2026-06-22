"""
Pipeline 'serving': bendice el modelo de producción (2015) a una ruta estable
que la API de FastAPI consume (data/09_serving/).
"""

from .pipeline import create_pipeline

__all__ = ["create_pipeline"]

__version__ = "0.1"
