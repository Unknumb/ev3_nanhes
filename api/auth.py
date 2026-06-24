"""Login por correo (magic-link) sin contraseñas.

Flujo:
  1. request_code(email)  -> genera un codigo de 6 digitos, guarda su SHA-256 con
     expiracion y lo envia por correo (reusa el mailer).
  2. verify_code(email, code) -> si coincide, emite un token de sesion firmado.
  3. verify_token(token)  -> devuelve el email si el token es valido y no expiro.

Tokens: HMAC-SHA256 con SECRET_KEY (stdlib, sin dependencias). No guardan estado
en el servidor; expiran por su campo `exp`. Protegen /history para que cada quien
vea SOLO su propio historial.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

from . import db, mailer

logger = logging.getLogger("ev3.api.auth")

CODE_LENGTH = 6                     # digitos del codigo de acceso
CODE_TTL_SECONDS = 10 * 60          # el codigo dura 10 min
TOKEN_TTL_SECONDS = 7 * 24 * 3600   # la sesion dura 7 dias
RESEND_COOLDOWN_SECONDS = 60        # rate-limit: 1 codigo por correo por minuto

_SECRET = os.getenv("SECRET_KEY")
if not _SECRET:
    _SECRET = secrets.token_hex(32)
    logger.warning(
        "SECRET_KEY no definida: usando una efimera (las sesiones no sobreviven "
        "reinicios). Definela en .env para produccion."
    )
_SECRET_BYTES = _SECRET.encode("utf-8")


def normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def _hash_code(email: str, code: str) -> str:
    # Liga el hash al correo: un codigo no sirve para otro email.
    return hashlib.sha256(f"{email}:{code}".encode()).hexdigest()


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign(body: str) -> str:
    return _b64e(hmac.new(_SECRET_BYTES, body.encode("ascii"), hashlib.sha256).digest())


def make_token(email: str) -> str:
    payload = {"email": email, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    body = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    return f"{body}.{_sign(body)}"


def verify_token(token: str | None) -> str | None:
    """Devuelve el email del token si la firma es valida y no expiro; si no, None."""
    if not token or "." not in token:
        return None
    body, _, sig = token.partition(".")
    if not hmac.compare_digest(sig, _sign(body)):
        return None
    try:
        payload = json.loads(_b64d(body))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    email = payload.get("email")
    return email if isinstance(email, str) else None


def request_code(email: str) -> dict:
    """Genera y envia un codigo de acceso. {ok, mode} o {ok: False, reason, retry_after?}."""
    email = normalize_email(email)
    if not mailer.valid_email(email):
        return {"ok": False, "reason": "email_invalido"}

    elapsed = db.seconds_since_last_code(email)
    if elapsed is not None and elapsed < RESEND_COOLDOWN_SECONDS:
        return {
            "ok": False,
            "reason": "cooldown",
            "retry_after": int(RESEND_COOLDOWN_SECONDS - elapsed),
        }

    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=CODE_TTL_SECONDS)
    db.save_login_code(email, _hash_code(email, code), expires_at)

    envio = mailer.send_login_code(email, code)
    return {"ok": bool(envio.get("ok")), "mode": envio.get("mode", "none")}


def verify_code(email: str, code: str) -> dict:
    """Verifica el codigo. {ok: True, token, email} o {ok: False, reason}."""
    email = normalize_email(email)
    code = (code or "").strip()
    if not mailer.valid_email(email):
        return {"ok": False, "reason": "email_invalido"}
    if not (code.isdigit() and len(code) == CODE_LENGTH):
        return {"ok": False, "reason": "formato"}

    estado = db.verify_login_code(email, _hash_code(email, code))
    if estado == "ok":
        return {"ok": True, "token": make_token(email), "email": email}
    return {"ok": False, "reason": estado}  # none | bad | expired | locked
