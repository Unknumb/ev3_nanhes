"""Envio de correo pluggable y best-effort.

- Si hay credenciales SMTP en el entorno (SMTP_HOST/SMTP_USER/SMTP_PASSWORD) ->
  envia el informe de verdad via smtplib.
- Si NO hay credenciales -> **modo demo**: escribe el HTML en `data/outbox/` y loguea
  "correo simulado". Asi la demo en Docker funciona sin secretos.

Nunca lanza: devuelve un dict con el resultado (mismo patron best-effort que `db.py`).
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

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "no-reply@nhanes-longevity.local")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def valid_email(value: str | None) -> bool:
    return bool(value and _EMAIL_RE.match(value))


def smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value)[:60]


def _write_outbox(to: str, subject: str, html: str) -> str:
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    path = OUTBOX_DIR / f"{ts}_{_slug(to)}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


def send_report(to: str, subject: str, html: str) -> dict:
    """Envia (o simula) el informe. Devuelve {ok, mode, detail}."""
    if not valid_email(to):
        return {"ok": False, "mode": "invalid", "detail": "email invalido"}

    if not smtp_configured():
        # Modo demo: persistir a outbox y loguear, sin secretos.
        try:
            path = _write_outbox(to, subject, html)
            logger.info("Correo SIMULADO (modo demo) para %s -> %s", to, path)
            return {"ok": True, "mode": "demo", "detail": path}
        except Exception as exc:  # pragma: no cover
            logger.warning("No se pudo escribir el outbox demo: %s", exc)
            return {"ok": False, "mode": "demo", "detail": str(exc)}

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to
        msg.set_content(
            "Tu informe de longevidad esta en formato HTML. Abrelo en un navegador."
        )
        msg.add_alternative(html, subtype="html")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("Correo enviado via SMTP a %s", to)
        return {"ok": True, "mode": "smtp", "detail": to}
    except Exception as exc:
        logger.warning("Fallo el envio SMTP a %s: %s", to, exc)
        return {"ok": False, "mode": "smtp", "detail": str(exc)}
