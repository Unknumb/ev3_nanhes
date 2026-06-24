"use client";

import { useEffect, useState } from "react";
import {
  AUTH_REQUEST_CODE_URL,
  AUTH_VERIFY_URL,
  HISTORY_URL,
  clearSessionToken,
  fetchWithTimeout,
  getFetchErrorMessage,
  getSessionToken,
  setSessionToken
} from "@/lib/api";

type Prediction = {
  created_at: string;
  es_longevo: boolean;
  probabilidad: number;
  edad_biologica: number;
  edad_cronologica: number | null;
  gap: number | null;
  riesgo_mortalidad_10y: number | null;
};

type HistoryResponse = {
  email: string;
  predicciones: Prediction[];
};

type Step = "email" | "code" | "history";

function formatDate(iso: string) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("es-CL", { dateStyle: "medium", timeStyle: "short" });
}

function formatGap(gap: number | null) {
  if (gap === null || gap === undefined) return "—";
  const rounded = Math.round(gap * 10) / 10;
  return `${rounded > 0 ? "+" : ""}${rounded}`;
}

export default function MisPrediccionesPage() {
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryResponse | null>(null);

  // Si ya hay sesión guardada, intenta cargar el historial directo.
  useEffect(() => {
    const token = getSessionToken();
    if (token) loadHistory(token);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadHistory(token: string) {
    setBusy(true);
    setError(null);
    try {
      const res = await fetchWithTimeout(HISTORY_URL, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.status === 401) {
        clearSessionToken();
        setStep("email");
        setError("Tu sesión expiró. Ingresa de nuevo.");
        return;
      }
      if (!res.ok) throw new Error(`La API respondió ${res.status}.`);
      const body = (await res.json()) as HistoryResponse;
      setHistory(body);
      setStep("history");
    } catch (err) {
      setError(getFetchErrorMessage(err, "No se pudo cargar tu historial."));
    } finally {
      setBusy(false);
    }
  }

  async function requestCode(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = email.trim();
    if (!trimmed) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const res = await fetchWithTimeout(AUTH_REQUEST_CODE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: trimmed })
      });
      const body = await res.json().catch(() => null);
      if (res.status === 429) {
        setError(body?.detail ?? "Espera un momento antes de pedir otro código.");
        return;
      }
      if (!res.ok) {
        setError(res.status === 422 ? "Ingresa un correo válido." : "No se pudo enviar el código.");
        return;
      }
      setStep("code");
      setNotice(
        body?.mode === "demo"
          ? `Modo demo: el código se guardó en data/outbox/ (configura SMTP para enviarlo de verdad).`
          : `Te enviamos un código de 6 dígitos a ${trimmed}. Revisa tu correo.`
      );
    } catch (err) {
      setError(getFetchErrorMessage(err, "No se pudo enviar el código."));
    } finally {
      setBusy(false);
    }
  }

  async function verifyCode(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const clean = code.trim();
    if (clean.length !== 6) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetchWithTimeout(AUTH_VERIFY_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), code: clean })
      });
      const body = await res.json().catch(() => null);
      if (!res.ok) {
        setError(body?.detail ?? "Código inválido.");
        return;
      }
      setSessionToken(body.token);
      setCode("");
      setNotice(null);
      await loadHistory(body.token);
    } catch (err) {
      setError(getFetchErrorMessage(err, "No se pudo verificar el código."));
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    clearSessionToken();
    setHistory(null);
    setCode("");
    setNotice(null);
    setError(null);
    setStep("email");
  }

  const inputCls =
    "min-h-11 w-full rounded-md border border-slate-300 px-3 text-sm outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100";
  const btnCls =
    "min-h-11 rounded-md bg-emerald-700 px-6 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-400";

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-950">
      <section className="mx-auto grid w-full max-w-5xl gap-8">
        <div>
          <p className="mb-3 text-sm font-medium uppercase tracking-wide text-emerald-700">
            NHANES Longevity
          </p>
          <h1 className="text-4xl font-semibold leading-tight sm:text-5xl">
            Mis predicciones
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            Tu historial es privado: para verlo, confirma que el correo es tuyo con
            un código de un solo uso. Así nadie más puede ver tus datos de salud.
          </p>
        </div>

        {/* Paso 1: pedir el correo */}
        {step === "email" && (
          <form
            className="grid gap-3 rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:grid-cols-[1fr_auto] sm:items-end"
            onSubmit={requestCode}
          >
            <label className="grid gap-1" htmlFor="login-email">
              <span className="text-sm font-medium text-slate-950">Tu correo</span>
              <input
                autoComplete="email"
                className={inputCls}
                id="login-email"
                onChange={(e) => setEmail(e.target.value)}
                placeholder="tucorreo@ejemplo.com"
                type="email"
                value={email}
              />
            </label>
            <button className={btnCls} disabled={busy} type="submit">
              {busy ? "Enviando..." : "Enviarme un código"}
            </button>
          </form>
        )}

        {/* Paso 2: ingresar el código */}
        {step === "code" && (
          <form
            className="grid gap-3 rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:grid-cols-[1fr_auto] sm:items-end"
            onSubmit={verifyCode}
          >
            <label className="grid gap-1" htmlFor="login-code">
              <span className="text-sm font-medium text-slate-950">
                Código de 6 dígitos
              </span>
              <input
                autoFocus
                className={`${inputCls} tracking-[0.4em]`}
                id="login-code"
                inputMode="numeric"
                maxLength={6}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                placeholder="000000"
                value={code}
              />
            </label>
            <div className="flex gap-2">
              <button className={btnCls} disabled={busy} type="submit">
                {busy ? "Verificando..." : "Entrar"}
              </button>
              <button
                className="min-h-11 rounded-md px-4 text-sm font-medium text-slate-500 hover:text-slate-900"
                onClick={() => {
                  setStep("email");
                  setError(null);
                  setNotice(null);
                }}
                type="button"
              >
                Cambiar correo
              </button>
            </div>
          </form>
        )}

        {notice && (
          <div className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
            {notice}
          </div>
        )}

        {error && (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            {error}
          </div>
        )}

        {/* Paso 3: historial */}
        {step === "history" && history && (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-slate-600">
                Sesión iniciada como <strong>{history.email}</strong>
              </p>
              <button
                className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
                onClick={logout}
                type="button"
              >
                Cerrar sesión
              </button>
            </div>

            {history.predicciones.length === 0 ? (
              <div className="rounded-md border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
                Aún no tienes predicciones guardadas. Al calcular tu edad biológica,
                marca <strong>“Guardar esta predicción”</strong> con este mismo correo.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                      <th className="px-4 py-3 font-semibold">Fecha</th>
                      <th className="px-4 py-3 font-semibold">Edad biológica</th>
                      <th className="px-4 py-3 font-semibold">Edad real</th>
                      <th className="px-4 py-3 font-semibold">Diferencia</th>
                      <th className="px-4 py-3 font-semibold">Prob. longevidad</th>
                      <th className="px-4 py-3 font-semibold">Riesgo 10 años</th>
                      <th className="px-4 py-3 font-semibold">Resultado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.predicciones.map((prediction, index) => {
                      const percent =
                        prediction.probabilidad <= 1
                          ? prediction.probabilidad * 100
                          : prediction.probabilidad;
                      return (
                        <tr
                          className="border-b border-slate-100 last:border-0"
                          key={`${prediction.created_at}-${index}`}
                        >
                          <td className="px-4 py-3 text-slate-600">
                            {formatDate(prediction.created_at)}
                          </td>
                          <td className="px-4 py-3 font-semibold text-slate-950">
                            {Math.round(prediction.edad_biologica)} años
                          </td>
                          <td className="px-4 py-3 text-slate-600">
                            {prediction.edad_cronologica !== null
                              ? `${Math.round(prediction.edad_cronologica)} años`
                              : "—"}
                          </td>
                          <td className="px-4 py-3 text-slate-600">
                            {formatGap(prediction.gap)}
                          </td>
                          <td className="px-4 py-3 text-slate-600">
                            {Math.round(percent)}%
                          </td>
                          <td className="px-4 py-3 text-slate-600">
                            {prediction.riesgo_mortalidad_10y != null
                              ? `${Math.round(prediction.riesgo_mortalidad_10y * 100)}%`
                              : "—"}
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={
                                prediction.es_longevo
                                  ? "rounded-md bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-800"
                                  : "rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700"
                              }
                            >
                              {prediction.es_longevo ? "Longevo" : "No longevo"}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>
    </main>
  );
}
