"""Envio del informe por correo: pluggable y best-effort.

Dos modos, elegidos automaticamente segun el entorno:

- **SMTP real** (opt-in): si estan `SMTP_HOST`, `SMTP_USER` y `SMTP_PASSWORD` en el
  entorno, envia el HTML por `smtplib` (STARTTLS).
- **Demo** (por defecto, cero secretos): escribe el informe en `data/outbox/` como
  `<timestamp>_<email>.html` y loguea "correo simulado". Asi el proyecto corre y se
  demuestra end-to-end sin credenciales.

Nunca lanza: devuelve un dict {ok, mode, detail} (mismo patron best-effort que db.py).
"""

from __future__ import annotations

import logging
import os
import re
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

logger = logging.getLogger("ev3.api.mailer")

_ROOT = Path(os.getenv("EV3_ROOT", Path(__file__).resolve().parent.parent))
OUTBOX_DIR = Path(os.getenv("MAIL_OUTBOX_DIR", _ROOT / "data" / "outbox"))

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def valid_email(email: str | None) -> bool:
    """Validacion ligera de formato de correo (no verifica que exista)."""
    return bool(email) and bool(_EMAIL_RE.match(email.strip()))


def smtp_configured() -> bool:
    """True si hay credenciales SMTP completas en el entorno."""
    return all(os.getenv(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))


def _slug(email: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", email.strip()) or "anon"


def _enviar_demo(
    to: str,
    subject: str,
    html: str,
    pdf: bytes | None = None,
    filename: str = "informe.pdf",
) -> dict:
    """Modo demo: persiste el correo (y el PDF adjunto) en data/outbox/."""
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    ruta = OUTBOX_DIR / f"{ts}_{_slug(to)}.html"
    ruta.write_text(html, encoding="utf-8")
    if pdf is not None:
        (OUTBOX_DIR / f"{ts}_{_slug(to)}.pdf").write_bytes(pdf)
    logger.info("Correo simulado (demo) escrito en %s", ruta)
    return {"ok": True, "mode": "demo", "detail": str(ruta)}


def _enviar_smtp(
    to: str,
    subject: str,
    html: str,
    pdf: bytes | None = None,
    filename: str = "informe.pdf",
) -> dict:
    """Modo real: envia por SMTP con STARTTLS, con PDF adjunto opcional."""
    host = os.environ["SMTP_HOST"]
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    sender = os.getenv("SMTP_FROM", user)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.set_content(
        "Tu informe de longevidad va en este correo. Si tu cliente no muestra el "
        "formato, abre el PDF adjunto."
    )
    msg.add_alternative(html, subtype="html")
    if pdf is not None:
        msg.add_attachment(
            pdf, maintype="application", subtype="pdf", filename=filename
        )

    with smtplib.SMTP(host, port, timeout=20) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
    logger.info("Correo enviado por SMTP a %s", to)
    return {"ok": True, "mode": "smtp", "detail": f"enviado a {to}"}


def send_html(
    to: str,
    subject: str,
    html: str,
    pdf: bytes | None = None,
    filename: str = "informe.pdf",
) -> dict:
    """Envia un correo HTML (con PDF adjunto opcional). Best-effort: nunca lanza.

    Modo: SMTP real si hay credenciales; si no, demo (escribe a data/outbox/).
    """
    if not valid_email(to):
        return {"ok": False, "mode": "none", "detail": "email invalido"}
    try:
        if smtp_configured():
            return _enviar_smtp(to, subject, html, pdf, filename)
        return _enviar_demo(to, subject, html, pdf, filename)
    except Exception as exc:  # pragma: no cover - depende del entorno SMTP
        logger.warning("Fallo el envio a %s: %s", to, exc)
        return {"ok": False, "mode": "error", "detail": str(exc)}


def send_report(to: str, subject: str, html: str) -> dict:
    """Envia el informe de longevidad (alias semantico de send_html)."""
    return send_html(to, subject, html)


def send_report_pdf(to: str, subject: str, body_html: str, pdf: bytes | None) -> dict:
    """Envia el informe con el PDF adjunto (cuerpo corto en HTML)."""
    return send_html(to, subject, body_html, pdf=pdf, filename="informe_longevidad.pdf")


def send_login_code(to: str, code: str) -> dict:
    """Envia el codigo de acceso de un solo uso (login por correo)."""
    html = (
        "<div style=\"font-family:system-ui,sans-serif;max-width:480px;margin:auto\">"
        "<h2 style=\"color:#047857\">Tu código de acceso</h2>"
        "<p>Usa este código para entrar a tu historial en NHANES Longevity:</p>"
        f"<p style=\"font-size:32px;font-weight:700;letter-spacing:6px;"
        f"background:#ecfdf5;color:#065f46;padding:16px;border-radius:12px;"
        f"text-align:center\">{code}</p>"
        "<p style=\"color:#64748b;font-size:14px\">Vence en 10 minutos. "
        "Si no lo pediste, ignora este correo.</p></div>"
    )
    return send_html(to, "Tu código de acceso - NHANES Longevity", html)
