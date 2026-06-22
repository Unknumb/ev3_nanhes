"use client";

import { useState } from "react";
import { HISTORY_URL, fetchWithTimeout, getFetchErrorMessage } from "@/lib/api";

type Prediction = {
  created_at: string;
  es_longevo: boolean;
  probabilidad: number;
  edad_biologica: number;
  edad_cronologica: number | null;
  gap: number | null;
};

type HistoryResponse = {
  email: string;
  predicciones: Prediction[];
};

type HistoryState =
  | { status: "idle"; data: null; error: null }
  | { status: "loading"; data: null; error: null }
  | { status: "success"; data: HistoryResponse; error: null }
  | { status: "error"; data: null; error: string };

function formatDate(iso: string) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString("es-CL", {
    dateStyle: "medium",
    timeStyle: "short"
  });
}

function formatGap(gap: number | null) {
  if (gap === null || gap === undefined) {
    return "—";
  }
  const rounded = Math.round(gap * 10) / 10;
  return `${rounded > 0 ? "+" : ""}${rounded}`;
}

export default function MisPrediccionesPage() {
  const [email, setEmail] = useState("");
  const [historyState, setHistoryState] = useState<HistoryState>({
    status: "idle",
    data: null,
    error: null
  });

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmed = email.trim();
    if (!trimmed) {
      return;
    }

    setHistoryState({ status: "loading", data: null, error: null });

    try {
      const response = await fetchWithTimeout(
        `${HISTORY_URL}?email=${encodeURIComponent(trimmed)}`
      );
      const body = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          response.status === 422
            ? "Ingresa un correo válido."
            : `La API respondió ${response.status} al consultar tu historial.`
        );
      }

      setHistoryState({
        status: "success",
        data: body as HistoryResponse,
        error: null
      });
    } catch (error) {
      setHistoryState({
        status: "error",
        data: null,
        error:
          error instanceof Error
            ? getFetchErrorMessage(error, "No se pudo consultar tu historial")
            : "No se pudo consultar tu historial"
      });
    }
  }

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
          <p className="mt-3 max-w-2xl text-sm text-slate-600">
            Consulta el historial asociado a tu correo. Solo verás resultados si al
            calcularlos marcaste la opción <strong>“Guardar esta predicción”</strong>.
            No usamos contraseñas: el correo es solo una etiqueta para reagrupar tus
            estimaciones.
          </p>
        </div>

        <form
          className="grid gap-3 rounded-md border border-slate-200 bg-white p-6 shadow-sm sm:grid-cols-[1fr_auto] sm:items-end"
          onSubmit={handleSubmit}
        >
          <label className="grid gap-1" htmlFor="history-email">
            <span className="text-sm font-medium text-slate-950">Tu correo</span>
            <input
              className="min-h-11 w-full rounded-md border border-slate-300 px-3 text-sm outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
              id="history-email"
              onChange={(event) => setEmail(event.target.value)}
              placeholder="tucorreo@ejemplo.com"
              type="email"
              value={email}
            />
          </label>
          <button
            className="min-h-11 rounded-md bg-emerald-700 px-6 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            disabled={historyState.status === "loading"}
            type="submit"
          >
            {historyState.status === "loading" ? "Consultando..." : "Ver mi historial"}
          </button>
        </form>

        {historyState.status === "error" && (
          <div className="rounded-md border border-red-200 bg-red-50 p-6 text-sm text-red-800">
            <p className="font-medium">No se pudo consultar tu historial</p>
            <p className="mt-2 text-xs">{historyState.error}</p>
          </div>
        )}

        {historyState.status === "success" &&
          historyState.data.predicciones.length === 0 && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
              No encontramos predicciones guardadas para{" "}
              <strong>{historyState.data.email}</strong>. Si quieres conservarlas,
              marca “Guardar esta predicción” al calcular tu edad biológica.
            </div>
          )}

        {historyState.status === "success" &&
          historyState.data.predicciones.length > 0 && (
            <div className="overflow-x-auto rounded-md border border-slate-200 bg-white shadow-sm">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-4 py-3 font-semibold">Fecha</th>
                    <th className="px-4 py-3 font-semibold">Edad biológica</th>
                    <th className="px-4 py-3 font-semibold">Edad real</th>
                    <th className="px-4 py-3 font-semibold">Gap</th>
                    <th className="px-4 py-3 font-semibold">Prob. longevidad</th>
                    <th className="px-4 py-3 font-semibold">Clasificación</th>
                  </tr>
                </thead>
                <tbody>
                  {historyState.data.predicciones.map((prediction, index) => {
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
      </section>
    </main>
  );
}
