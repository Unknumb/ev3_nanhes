"""API FastAPI: sirve el modelo de longevidad combinado (clasificacion + regresion).

Endpoints:
  GET  /health             -> liveness + si los modelos y la BD estan listos
  GET  /schema             -> feature_schema.json (el front renderiza el form desde aqui)
  POST /predict            -> es_longevo, probabilidad, edad biologica, gap (persiste en BD)
  POST /explain            -> contribuciones SHAP por feature (requiere shap instalado)
  GET  /feature-importance -> importancia global de features (graficos del front)
  POST /report             -> informe HTML; lo envia por correo y/o lo persiste
  POST /auth/request-code  -> envia un codigo de acceso de un solo uso al correo
  POST /auth/verify        -> verifica el codigo y devuelve un token de sesion
  GET  /history            -> historial del USUARIO AUTENTICADO (requiere token)
  GET  /metrics            -> reportes de entrenamiento (accuracy / MAE) en texto
  GET  /aggregates         -> agregados del historial para el dashboard ejecutivo

Ejecutar desde la raiz del repo (local):
  uvicorn api.main:app --reload          # escucha solo en 127.0.0.1

En un servidor (EC2/produccion) hay que escuchar en TODAS las interfaces, o las
peticiones de afuera nunca llegan (se quedan colgadas hasta el timeout del front):
  uvicorn api.main:app --host 0.0.0.0 --port 8000
  # ademas: exportar CORS_ORIGINS con el origen publico del frontend (ver abajo)
  # y abrir el puerto 8000 en el Security Group de EC2.
"""

from __future__ import annotations

import base64
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import auth, db, mailer, report
from . import model_registry as registry
from .schema import (
    AuthCodeRequest,
    AuthVerifyRequest,
    PredictRequest,
    PredictResponse,
    validate_features,
)

logger = logging.getLogger("ev3.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    try:
        registry.load_models()
    except Exception as exc:
        logger.warning("No se pudieron cargar los modelos al iniciar la API: %s", exc)
    yield


app = FastAPI(
    title="NHANES Longevity API",
    version="0.1.0",
    description="Predice longevidad (IS_LONGEVO) y edad biologica desde biomarcadores NHANES.",
    lifespan=lifespan,
)

# En produccion DEBE setearse CORS_ORIGINS con el origen publico del frontend
# (p.ej. "http://<IP_o_dominio>" o "https://tuedad.me"); el default solo sirve
# para desarrollo local y el navegador bloqueara las llamadas del front desplegado.
_raw_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "models_ready": registry.models_ready(),
        "db_ready": db.db_ready(),
    }


@app.get("/schema")
def schema() -> dict:
    return registry.load_schema()


def _require_models() -> None:
    if not registry.models_ready():
        raise HTTPException(
            status_code=503,
            detail="Modelos no disponibles. Corre: kedro run --pipeline serving",
        )


def _riesgo_mortalidad(
    features: dict, edad: float | None
) -> float | None:
    """Riesgo de mortalidad a 10 años (0-1) si hay edad y modelo. Best-effort."""
    if edad is None or not registry.mortality_ready():
        return None
    try:
        res = registry.predict_mortality({**features, "RIDAGEYR": edad})
        return res.get("riesgo_10y")
    except Exception:  # pragma: no cover
        return None


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    _require_models()
    errores = validate_features(req.features)
    if errores:
        raise HTTPException(status_code=422, detail=errores)
    resultado = registry.predict(req.features, req.edad_cronologica)
    riesgo = _riesgo_mortalidad(req.features, req.edad_cronologica)
    db.save_prediction(
        resultado, req.features, email=req.email, consent_save=req.guardar,
        riesgo_mortalidad=riesgo,
    )
    return PredictResponse(**resultado)


@app.post("/explain")
def explain(req: PredictRequest) -> dict:
    _require_models()
    errores = validate_features(req.features)
    if errores:
        raise HTTPException(status_code=422, detail=errores)
    try:
        return registry.explain(req.features)
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc


@app.get("/feature-importance")
def feature_importance(
    top_n: int = Query(10, ge=1, le=23),
    model: str = Query("clasificacion", pattern="^(clasificacion|regresion)$"),
    clinical_only: bool = Query(False),
) -> dict:
    """Importancia GLOBAL de features (para los graficos introductorios del front).

    `clinical_only=true` deja solo biomarcadores (antropometria/presion/laboratorio +
    sexo): es el mensaje honesto para el publico, ya que los campos demograficos
    actuan como proxy de edad por el data augmentation del entrenamiento.
    """
    _require_models()
    return registry.global_importance(
        top_n=top_n, model_name=model, clinical_only=clinical_only
    )


@app.post("/predict-mortality")
def predict_mortality(req: PredictRequest) -> dict:
    """MVP: riesgo de mortalidad a 10 años. `features` debe incluir `RIDAGEYR` (edad).

    Modelo separado del de edad biológica (ver docs/prediccion_mortalidad.md).
    """
    if not registry.mortality_ready():
        raise HTTPException(
            status_code=503,
            detail="Modelo de mortalidad no disponible. Corre el pipeline nhanes_mortality.",
        )
    edad = req.features.get("RIDAGEYR")
    if edad is None:
        raise HTTPException(status_code=422, detail="Falta la edad (RIDAGEYR).")
    return registry.predict_mortality(req.features)


@app.post("/report")
def build_report(req: PredictRequest) -> dict:
    """Genera el informe HTML, opcionalmente lo envia por correo y lo persiste.

    Devuelve el HTML para descarga inmediata en el front. Si `email` es valido,
    intenta enviarlo (modo demo a data/outbox/ si no hay SMTP). Si ademas `guardar`
    es True, persiste la prediccion asociada al correo.
    """
    _require_models()
    errores = validate_features(req.features)
    if errores:
        raise HTTPException(status_code=422, detail=errores)

    resultado = registry.predict(req.features, req.edad_cronologica)

    # Riesgo de mortalidad a 10 años (modelo aparte; necesita la edad). Best-effort.
    riesgo = _riesgo_mortalidad(req.features, req.edad_cronologica)
    mortalidad = {"riesgo_10y": riesgo, "riesgo_pct": round(riesgo * 100, 1)} if riesgo is not None else None

    db.save_prediction(
        resultado, req.features, email=req.email, consent_save=req.guardar,
        riesgo_mortalidad=riesgo,
    )

    explicacion = None
    try:
        explicacion = registry.explain(req.features)
    except Exception as exc:  # shap opcional: el informe igual se genera
        logger.info("Informe sin SHAP (explain no disponible): %s", exc)

    html = report.build_report_html(
        resultado, req.features, registry.load_schema(),
        explain=explicacion, mortalidad=mortalidad,
    )
    pdf = report.build_report_pdf(html)  # bytes o None si xhtml2pdf no está

    emailed, email_mode = False, "none"
    if req.email:
        if not mailer.valid_email(req.email):
            raise HTTPException(status_code=422, detail="Email invalido")
        envio = mailer.send_report_pdf(
            req.email,
            "Tu informe de longevidad",
            report.build_email_body(resultado),
            pdf,
        )
        emailed, email_mode = envio["ok"], envio["mode"]

    return {
        "html": html,
        "pdf_base64": base64.b64encode(pdf).decode("ascii") if pdf else None,
        "emailed": emailed,
        "email_mode": email_mode,
        "guardado": bool(req.guardar and req.email),
    }


# ── Autenticacion por correo (magic-link) ──────────────────────────────────
_bearer = HTTPBearer(auto_error=False)

_AUTH_ERRORS = {
    "bad": "Codigo incorrecto.",
    "expired": "El codigo vencio. Pide uno nuevo.",
    "none": "No hay un codigo activo. Pide uno nuevo.",
    "locked": "Demasiados intentos. Pide un codigo nuevo.",
    "formato": "El codigo son 6 digitos.",
    "email_invalido": "Email invalido.",
}


def current_email(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Dependencia: exige un token de sesion valido y devuelve su correo."""
    email = auth.verify_token(creds.credentials if creds else None)
    if not email:
        raise HTTPException(
            status_code=401, detail="Inicia sesion para ver tu historial."
        )
    return email


@app.post("/auth/request-code")
def auth_request_code(req: AuthCodeRequest) -> dict:
    """Envia un codigo de acceso de un solo uso al correo indicado."""
    res = auth.request_code(req.email)
    if not res["ok"]:
        if res.get("reason") == "email_invalido":
            raise HTTPException(status_code=422, detail="Email invalido.")
        if res.get("reason") == "cooldown":
            raise HTTPException(
                status_code=429,
                detail=f"Espera {res['retry_after']}s para pedir otro codigo.",
            )
    # No revelamos si el correo "existe": si es valido, el codigo va a su inbox.
    return {"ok": res["ok"], "mode": res.get("mode", "none")}


@app.post("/auth/verify")
def auth_verify(req: AuthVerifyRequest) -> dict:
    """Verifica el codigo y devuelve un token de sesion (valido 7 dias)."""
    res = auth.verify_code(req.email, req.code)
    if not res["ok"]:
        raise HTTPException(
            status_code=401,
            detail=_AUTH_ERRORS.get(res.get("reason", ""), "Codigo invalido."),
        )
    return {"token": res["token"], "email": res["email"]}


@app.get("/history")
def history(email: str = Depends(current_email)) -> dict:
    """Historial del USUARIO AUTENTICADO (solo lo que guardo con consentimiento).

    El correo se deriva del token de sesion, no de un parametro: nadie puede
    consultar el historial de otra persona.
    """
    try:
        predicciones = db.get_history(email)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"BD no disponible: {exc}") from exc
    return {"email": email, "predicciones": predicciones}


@app.get("/aggregates")
def aggregates() -> dict:
    try:
        return db.get_aggregates()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"BD no disponible: {exc}") from exc


@app.get("/metrics")
def metrics() -> dict:
    reportes_dir = Path(registry._ROOT) / "data" / "08_reporting"
    # El modelo de produccion es el combinado; si aun no se reentreno, caemos al
    # baseline 2015 para no romper el dashboard.
    candidatos = [
        ("reporte_clasificacion_combined.txt", "reporte_regresion_combined.txt"),
        ("reporte_clasificacion_2015.txt", "reporte_regresion_2015.txt"),
    ]
    clf_name, reg_name = next(
        (par for par in candidatos if (reportes_dir / par[0]).exists()),
        candidatos[0],
    )
    out: dict[str, str] = {}
    for nombre in (clf_name, reg_name):
        ruta = reportes_dir / nombre
        out[nombre] = (
            ruta.read_text(encoding="utf-8") if ruta.exists() else "(no disponible)"
        )
    # Modelo de mortalidad a 10 años (si está entrenado): se suma a las métricas.
    ruta_mort = reportes_dir / "reporte_mortalidad_10y.txt"
    if ruta_mort.exists():
        out["reporte_mortalidad_10y.txt"] = ruta_mort.read_text(encoding="utf-8")
    return out
