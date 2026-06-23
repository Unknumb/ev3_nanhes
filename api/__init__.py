"""API FastAPI de NHANES Longevity (capa de serving del modelo combinado)."""

# Carga el .env del repo ANTES de importar submodulos: db/mailer/auth leen
# variables de entorno al importarse (DATABASE_URL, SMTP_*, SECRET_KEY).
# Best-effort: si python-dotenv no esta instalado o no hay .env, se ignora.
import os as _os
from pathlib import Path as _Path

try:
    from dotenv import load_dotenv as _load_dotenv

    _root = _Path(_os.getenv("EV3_ROOT", _Path(__file__).resolve().parent.parent))
    _load_dotenv(_root / ".env")
except Exception:  # pragma: no cover - entorno sin python-dotenv
    pass
