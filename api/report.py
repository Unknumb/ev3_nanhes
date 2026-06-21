"""Genera el informe de longevidad en HTML autocontenido.

El mismo HTML sirve para (1) descargarlo desde el front y (2) como cuerpo del correo
(ver `mailer.py`). Sin dependencias de plantillas ni de generacion de PDF: estilos
inline + f-strings. Quien quiera PDF puede imprimir desde el navegador.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any

_DISCLAIMER = (
    "Proyecto academico/educativo. No es consejo medico ni diagnostico. "
    "La 'edad biologica' es una estimacion poblacional a partir de biomarcadores "
    "NHANES (CDC), no una medicion clinica."
)


def _gap_texto(gap: float | None) -> str:
    if gap is None:
        return "Sin edad de referencia para comparar."
    if gap > 1:
        return f"Tu cuerpo aparenta {abs(gap):.0f} ano(s) MAS que tu edad real."
    if gap < -1:
        return f"Tu cuerpo aparenta {abs(gap):.0f} ano(s) MENOS que tu edad real."
    return "Tu edad biologica esta alineada con tu edad real."


def _fmt(value: Any) -> str:
    if value is None:
        return "No informado"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _tabla_datos(features: dict[str, Any], schema: dict) -> str:
    labels = {f["code"]: f["label"] for f in schema["features"]}
    units = {f["code"]: f.get("unit", "") for f in schema["features"]}
    # Mapear el value categorico a su etiqueta legible cuando exista.
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
    return "".join(filas) or "<tr><td style='padding:6px 10px'>Sin datos ingresados</td></tr>"


def _tabla_factores(explain: dict | None) -> str:
    if not explain or not explain.get("contribuciones"):
        return ""
    filas = []
    for c in explain["contribuciones"][:6]:
        sentido = "Hacia mayor longevidad" if c["empuja"] == "longevo" else "Hacia menor longevidad"
        color = "#047857" if c["empuja"] == "longevo" else "#b91c1c"
        filas.append(
            f"<tr><td style='padding:6px 10px;border-bottom:1px solid #e2e8f0'>{html.escape(str(c['feature']))}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #e2e8f0;text-align:right;color:{color}'>"
            f"{html.escape(sentido)}</td></tr>"
        )
    cuerpo = "".join(filas)
    return f"""
    <h2 style="font-size:18px;color:#0f172a;margin:28px 0 8px">Que mas influyo en tu resultado</h2>
    <table style="width:100%;border-collapse:collapse;font-size:14px">{cuerpo}</table>
    """


def build_report_html(
    result: dict[str, Any],
    features: dict[str, Any],
    schema: dict,
    explain: dict | None = None,
) -> str:
    """Arma el informe HTML completo a partir de la prediccion y los datos del usuario."""
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    prob_pct = round(result["probabilidad"] * 100) if result["probabilidad"] <= 1 else round(result["probabilidad"])
    edad_bio = result.get("edad_biologica")
    edad_cron = result.get("edad_cronologica")
    gap = result.get("gap")
    es_longevo = result.get("es_longevo")

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tu informe de longevidad</title></head>
<body style="margin:0;background:#f8fafc;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#0f172a">
  <div style="max-width:640px;margin:0 auto;padding:24px">
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:28px">
      <p style="text-transform:uppercase;letter-spacing:.08em;font-size:12px;color:#047857;font-weight:600;margin:0">
        NHANES Longevity
      </p>
      <h1 style="font-size:26px;margin:6px 0 2px">Tu informe de longevidad</h1>
      <p style="color:#64748b;font-size:13px;margin:0 0 20px">Generado el {fecha}</p>

      <div style="display:flex;gap:12px;flex-wrap:wrap">
        <div style="flex:1;min-width:150px;background:#f1f5f9;border-radius:10px;padding:16px">
          <p style="margin:0;color:#64748b;font-size:13px">Edad biologica estimada</p>
          <p style="margin:6px 0 0;font-size:30px;font-weight:700">{_fmt(edad_bio)} anos</p>
        </div>
        <div style="flex:1;min-width:150px;background:#f1f5f9;border-radius:10px;padding:16px">
          <p style="margin:0;color:#64748b;font-size:13px">Tu edad real</p>
          <p style="margin:6px 0 0;font-size:30px;font-weight:700">{_fmt(edad_cron) if edad_cron is not None else "—"}{" anos" if edad_cron is not None else ""}</p>
        </div>
      </div>

      <div style="margin-top:14px;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:10px;padding:16px">
        <p style="margin:0;font-weight:600">{html.escape(_gap_texto(gap))}</p>
      </div>

      <h2 style="font-size:18px;margin:28px 0 8px">Probabilidad de longevidad (vivir 70+ anos)</h2>
      <div style="background:#e2e8f0;border-radius:999px;height:16px;overflow:hidden">
        <div style="width:{prob_pct}%;height:100%;background:#047857"></div>
      </div>
      <p style="margin:8px 0 0;font-size:24px;font-weight:700">{prob_pct}%
        <span style="font-size:14px;font-weight:500;color:#64748b">
          ({"clasifica como longevo" if es_longevo else "no clasifica como longevo"})
        </span>
      </p>

      {_tabla_factores(explain)}

      <h2 style="font-size:18px;margin:28px 0 8px">Datos que ingresaste</h2>
      <table style="width:100%;border-collapse:collapse;font-size:14px">{_tabla_datos(features, schema)}</table>

      <p style="margin:28px 0 0;color:#94a3b8;font-size:12px;line-height:1.5">{html.escape(_DISCLAIMER)}</p>
    </div>
  </div>
</body></html>"""
