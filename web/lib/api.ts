export const NEXT_PUBLIC_API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const SCHEMA_URL = `${NEXT_PUBLIC_API_URL}/schema`;

export const PREDICT_URL = `${NEXT_PUBLIC_API_URL}/predict`;

export const MORTALITY_URL = `${NEXT_PUBLIC_API_URL}/predict-mortality`;

export const EXPLAIN_URL = `${NEXT_PUBLIC_API_URL}/explain`;

export const METRICS_URL = `${NEXT_PUBLIC_API_URL}/metrics`;

export const AGGREGATES_URL = `${NEXT_PUBLIC_API_URL}/aggregates`;

export const FEATURE_IMPORTANCE_URL = `${NEXT_PUBLIC_API_URL}/feature-importance`;

export const REPORT_URL = `${NEXT_PUBLIC_API_URL}/report`;

export const HISTORY_URL = `${NEXT_PUBLIC_API_URL}/history`;

export const AUTH_REQUEST_CODE_URL = `${NEXT_PUBLIC_API_URL}/auth/request-code`;

export const AUTH_VERIFY_URL = `${NEXT_PUBLIC_API_URL}/auth/verify`;

// ── Sesión (login por correo): token guardado en localStorage ────────────────
const SESSION_TOKEN_KEY = "ev3_session_token";

export function getSessionToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(SESSION_TOKEN_KEY);
}

export function setSessionToken(token: string): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(SESSION_TOKEN_KEY, token);
  }
}

export function clearSessionToken(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(SESSION_TOKEN_KEY);
  }
}

export const DEFAULT_FETCH_TIMEOUT_MS = 8000;

export async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit = {},
  timeoutMs = DEFAULT_FETCH_TIMEOUT_MS
) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(input, {
      ...init,
      signal: controller.signal
    });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export function getFetchErrorMessage(error: unknown, fallback: string) {
  if (error instanceof DOMException && error.name === "AbortError") {
    return "La API no respondió a tiempo. Revisa que el backend esté levantado.";
  }

  if (error instanceof TypeError) {
    return "No se pudo conectar con la API. Revisa que el backend esté levantado.";
  }

  return error instanceof Error ? error.message : fallback;
}
