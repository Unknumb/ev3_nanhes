"""Genera el informe de longevidad: HTML claro + PDF adjunto al correo.

- `build_report_html` arma un informe en lenguaje simple, con tablas e inline
  styles (compatible tanto con clientes de correo como con el motor de PDF).
- `build_report_pdf` convierte ese HTML a PDF (xhtml2pdf, sin dependencias de
  sistema). Si la librería no está instalada, devuelve None (best-effort).
- `build_email_body` es un cuerpo de correo corto; el informe completo va adjunto.
"""

from __future__ import annotations

import html
import io
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("ev3.api.report")

# Motor de PDF (opcional): import perezoso a nivel de módulo para degradar limpio.
try:
    from xhtml2pdf import pisa as _pisa
except ImportError:  # pragma: no cover - entorno sin xhtml2pdf
    _pisa = None

# Umbrales del texto explicativo del % de "parecido con un perfil de 70+".
_SIM_BAJA = 40
_SIM_ALTA = 70

_DISCLAIMER = (
    "Proyecto academico/educativo. No es consejo medico ni diagnostico. "
    "La 'edad biologica' es una estimacion poblacional a partir de biomarcadores "
    "NHANES (CDC), no una medicion clinica."
)


def _fmt(value: Any) -> str:
    if value is None:
        return "No informado"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _gap_texto(gap: float | None) -> str:
    if gap is None:
        return "No ingresaste tu edad real, asi que no podemos comparar."
    if gap > 1:
        return f"Tu cuerpo aparenta unos {abs(gap):.0f} ano(s) MAS que tu edad real."
    if gap < -1:
        return f"Tu cuerpo aparenta unos {abs(gap):.0f} ano(s) MENOS que tu edad real."
    return "Tu edad biologica esta alineada con tu edad real."


def _similitud_texto(pct: int) -> str:
    """Explica en simple qué significa el % de 'longevidad' (parecido con 70+)."""
    if pct < _SIM_BAJA:
        detalle = (
            "Un valor bajo significa que tu perfil se ve mas joven que el de una "
            "persona mayor, lo cual es lo esperable y saludable."
        )
    elif pct > _SIM_ALTA:
        detalle = (
            "Un valor alto significa que tu perfil se parece al de una persona de "
            "70 anos o mas."
        )
    else:
        detalle = "Un valor intermedio: tu perfil esta entre ambos extremos."
    return (
        "Mide cuanto tus biomarcadores se parecen a los de una persona de 70 anos "
        "o mas. <b>No</b> es tu probabilidad de vivir mucho. " + detalle
    )


def _tabla_datos(features: dict[str, Any], schema: dict) -> str:
    labels = {f["code"]: f["label"] for f in schema["features"]}
    units = {f["code"]: f.get("unit", "") for f in schema["features"]}
    opt_labels: dict[str, dict[Any, str]] = {
        f["code"]: {o["value"]: o["label"] for o in f.get("options", [])}
        for f in schema["features"]
        if f.get("type") == "categorical"
    }
    filas = []
    for code, val in features.items():
        if val is None:
            continue
        label = labels.get(code, code)
        shown = opt_labels.get(code, {}).get(val, _fmt(val))
        unit = units.get(code, "")
        filas.append(
            f"<tr><td style='padding:6px 10px;border-bottom:1px solid #e2e8f0'>{html.escape(label)}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #e2e8f0;text-align:right'>"
            f"{html.escape(str(shown))} {html.escape(unit)}</td></tr>"
        )
    return "".join(filas) or (
        "<tr><td style='padding:6px 10px'>Sin datos ingresados</td></tr>"
    )


def _tabla_factores(explain: dict | None, schema: dict) -> str:
    if not explain or not explain.get("contribuciones"):
        return ""
    labels = {f["code"]: f["label"] for f in schema["features"]}
    filas = []
    for c in explain["contribuciones"][:6]:
        nombre = labels.get(c["feature"], c["feature"])
        if c["empuja"] == "longevo":
            sentido, color = "Perfil de mayor edad", "#b45309"
        else:
            sentido, color = "Perfil mas joven", "#047857"
        filas.append(
            f"<tr><td style='padding:6px 10px;border-bottom:1px solid #e2e8f0'>{html.escape(str(nombre))}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #e2e8f0;text-align:right;color:{color}'>"
            f"{html.escape(sentido)}</td></tr>"
        )
    cuerpo = "".join(filas)
    return f"""
    <h2 style="font-size:17px;color:#0f172a;margin:26px 0 4px">Que mas influyo en tu resultado</h2>
    <p style="margin:0 0 8px;color:#64748b;font-size:13px">Los factores que mas pesaron al estimar tu edad biologica.</p>
    <table style="width:100%;border-collapse:collapse;font-size:14px">{cuerpo}</table>
    """


def build_report_html(
    result: dict[str, Any],
    features: dict[str, Any],
    schema: dict,
    explain: dict | None = None,
) -> str:
    """Informe completo en HTML (sirve para el PDF). Tablas + inline styles."""
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    prob = result["probabilidad"]
    prob_pct = round(prob * 100) if prob <= 1 else round(prob)
    edad_bio = result.get("edad_biologica")
    edad_cron = result.get("edad_cronologica")
    gap = result.get("gap")
    edad_cron_str = f"{_fmt(edad_cron)} anos" if edad_cron is not None else "—"

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>Tu informe de longevidad</title></head>
<body style="background:#ffffff;font-family:Helvetica,Arial,sans-serif;color:#0f172a">
  <div style="padding:8px 16px">
    <p style="font-size:11px;color:#047857;font-weight:bold;margin:0">NHANES LONGEVITY</p>
    <h1 style="font-size:24px;margin:4px 0 2px">Tu informe de longevidad</h1>
    <p style="color:#64748b;font-size:12px;margin:0 0 16px">Generado el {fecha}</p>

    <div style="background:#f1f5f9;padding:14px;margin-bottom:8px">
      <p style="margin:0;color:#64748b;font-size:12px">Tu edad biologica estimada</p>
      <p style="margin:4px 0 0;font-size:28px;font-weight:bold;color:#047857">{_fmt(edad_bio)} anos</p>
    </div>
    <div style="background:#f1f5f9;padding:14px">
      <p style="margin:0;color:#64748b;font-size:12px">Tu edad real</p>
      <p style="margin:4px 0 0;font-size:28px;font-weight:bold">{edad_cron_str}</p>
    </div>

    <div style="margin-top:12px;background:#ecfdf5;border:1px solid #a7f3d0;padding:12px">
      <p style="margin:0;font-weight:bold;font-size:15px">{html.escape(_gap_texto(gap))}</p>
      <p style="margin:6px 0 0;color:#475569;font-size:12px">
        La "edad biologica" es cuanto aparenta tu cuerpo segun tus biomarcadores,
        comparado con la poblacion. Es una estimacion, no un diagnostico.
      </p>
    </div>

    <h2 style="font-size:16px;margin:22px 0 4px">Parecido con un perfil de 70+ anos: {prob_pct}%</h2>
    <p style="margin:4px 0 0;color:#475569;font-size:12px;line-height:1.5">{_similitud_texto(prob_pct)}</p>

    {_tabla_factores(explain, schema)}

    <h2 style="font-size:16px;margin:22px 0 4px">Datos que ingresaste</h2>
    <table style="width:100%;border-collapse:collapse;font-size:13px">{_tabla_datos(features, schema)}</table>

    <p style="margin:22px 0 0;color:#94a3b8;font-size:10px;line-height:1.5">{html.escape(_DISCLAIMER)}</p>
  </div>
</body></html>"""


def build_email_body(result: dict[str, Any]) -> str:
    """Cuerpo corto del correo; el informe completo va adjunto en PDF."""
    edad_bio = result.get("edad_biologica")
    gap = result.get("gap")
    return (
        "<div style=\"font-family:Helvetica,Arial,sans-serif;max-width:520px;color:#0f172a\">"
        "<h2 style=\"color:#047857\">Tu informe de longevidad</h2>"
        f"<p>Tu edad biologica estimada es <b>{_fmt(edad_bio)} anos</b>. "
        f"{html.escape(_gap_texto(gap))}</p>"
        "<p>Adjuntamos tu <b>informe completo en PDF</b> con el detalle y los "
        "factores que mas influyeron.</p>"
        "<p style=\"color:#94a3b8;font-size:12px\">Proyecto academico/educativo. "
        "No es consejo medico ni diagnostico.</p></div>"
    )


def build_report_pdf(report_html: str) -> bytes | None:
    """Convierte el informe HTML a PDF. Best-effort: None si xhtml2pdf no está."""
    if _pisa is None:
        logger.warning("xhtml2pdf no instalado: no se genera PDF.")
        return None
    buffer = io.BytesIO()
    estado = _pisa.CreatePDF(src=report_html, dest=buffer, encoding="utf-8")
    if estado.err:  # pragma: no cover
        logger.warning("Fallo la generacion del PDF (%s errores).", estado.err)
        return None
    return buffer.getvalue()
