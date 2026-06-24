"use client";

import { useEffect, useMemo, useState } from "react";
import { METRICS_URL, fetchWithTimeout, getFetchErrorMessage } from "@/lib/api";
import { parseReportMetrics } from "@/lib/metrics";

type MetricsResponse = Record<string, string>;

type MetricsState =
  | { status: "loading"; data: null; error: null }
  | { status: "success"; data: MetricsResponse; error: null }
  | { status: "error"; data: null; error: string };

// ── Presentacion amigable de cada metrica (lenguaje simple, sin jerga ML) ──
type Render = "pct" | "score" | "years";
type MetricMeta = {
  titulo: string;
  emoji: string;
  render: Render;
  explica: (v: number) => string;
};

const METRIC_META: Record<string, MetricMeta> = {
  accuracy: {
    titulo: "Tasa de acierto",
    emoji: "🎯",
    render: "pct",
    explica: (v) =>
      `De cada 100 personas, el modelo acierta en ~${Math.round(
        v * 100
      )} al decir si llegarán a ser longevas (≥70 años) o no.`
  },
  f1: {
    titulo: "Equilibrio (F1)",
    emoji: "⚖️",
    render: "score",
    explica: () =>
      "Acierta de forma pareja en ambos grupos (longevos y no), sin sesgarse hacia el más común. Va de 0 a 1: cuanto más alto, mejor."
  },
  precision: {
    titulo: "Precisión",
    emoji: "✅",
    render: "pct",
    explica: (v) =>
      `Cuando el modelo dice "longevo", acierta el ${Math.round(
        v * 100
      )}% de las veces.`
  },
  recall: {
    titulo: "Cobertura",
    emoji: "🔍",
    render: "pct",
    explica: (v) =>
      `De todas las personas longevas reales, el modelo detecta el ${Math.round(
        v * 100
      )}%.`
  },
  roc_auc: {
    titulo: "Capacidad de distinguir",
    emoji: "📈",
    render: "score",
    explica: () =>
      "Qué tan bien separa a un longevo de un no-longevo tomados al azar. 0.5 sería pura suerte; 1 sería perfecto."
  },
  mae: {
    titulo: "Error típico de edad",
    emoji: "📏",
    render: "years",
    explica: (v) =>
      `En promedio, la edad biológica estimada se aleja unos ${v.toFixed(
        1
      )} años de la edad real. Menos es mejor.`
  },
  rmse: {
    titulo: "Error (castiga fallos grandes)",
    emoji: "📐",
    render: "years",
    explica: (v) =>
      `Parecido al error de edad, pero penaliza más los errores grandes (~${v.toFixed(
        1
      )} años).`
  },
  r2: {
    titulo: "Poder explicativo (R²)",
    emoji: "🧩",
    render: "pct",
    explica: (v) =>
      `El modelo explica el ${Math.round(
        v * 100
      )}% de las diferencias de edad entre personas. 100% sería perfecto.`
  }
};

// Orden de aparicion preferido por reporte (clasificacion vs regresion).
const ORDEN: string[] = [
  "accuracy",
  "f1",
  "precision",
  "recall",
  "roc_auc",
  "mae",
  "rmse",
  "r2"
];

function friendlyReport(reportName: string): { titulo: string; subtitulo: string } {
  const lower = reportName.toLowerCase();
  if (lower.includes("clasific")) {
    return {
      titulo: "Modelo 1 · ¿Llegará a ser longevo/a?",
      subtitulo: "Responde sí o no (vivir hasta los 70+). Tipo: clasificación."
    };
  }
  if (lower.includes("regres")) {
    return {
      titulo: "Modelo 2 · ¿Qué edad biológica aparenta?",
      subtitulo: "Estima la edad del cuerpo en años. Tipo: regresión."
    };
  }
  if (lower.includes("mortalidad")) {
    return {
      titulo: "Modelo 3 · ¿Riesgo de mortalidad a 10 años?",
      subtitulo:
        "Probabilidad de fallecer en los próximos 10 años según el perfil. Tipo: clasificación."
    };
  }
  return { titulo: reportName, subtitulo: "" };
}

function barColor(v: number): string {
  if (v >= 0.8) return "bg-emerald-500";
  if (v >= 0.6) return "bg-amber-500";
  return "bg-rose-500";
}

function valueLabel(render: Render, v: number): string {
  if (render === "pct") return `${Math.round(v * 100)}%`;
  if (render === "years") return `±${v.toFixed(1)} años`;
  return v.toFixed(2);
}

function MetricCard({ metricKey, value }: { metricKey: string; value: number }) {
  const meta = METRIC_META[metricKey];
  if (!meta) return null;
  const showBar = meta.render !== "years";
  const pct = Math.max(0, Math.min(100, value * 100));

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-sm font-medium text-slate-700">
          <span className="mr-1.5" aria-hidden>
            {meta.emoji}
          </span>
          {meta.titulo}
        </p>
        <p className="text-2xl font-bold text-slate-950">
          {valueLabel(meta.render, value)}
        </p>
      </div>

      {showBar && (
        <div className="mt-3 h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className={`h-full rounded-full ${barColor(value)} transition-all`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}

      <p className="mt-3 text-sm leading-6 text-slate-600">{meta.explica(value)}</p>
    </div>
  );
}

export default function MetricsPage() {
  const [metricsState, setMetricsState] = useState<MetricsState>({
    status: "loading",
    data: null,
    error: null
  });

  useEffect(() => {
    let isMounted = true;

    async function loadMetrics() {
      try {
        const response = await fetchWithTimeout(METRICS_URL);

        if (!response.ok) {
          throw new Error(`La API respondió ${response.status} al cargar las métricas`);
        }

        const metrics = (await response.json()) as MetricsResponse;

        if (isMounted) {
          setMetricsState({ status: "success", data: metrics, error: null });
        }
      } catch (error) {
        if (isMounted) {
          setMetricsState({
            status: "error",
            data: null,
            error:
              error instanceof Error
                ? getFetchErrorMessage(error, "No se pudieron cargar las métricas")
                : "No se pudieron cargar las métricas"
          });
        }
      }
    }

    loadMetrics();

    return () => {
      isMounted = false;
    };
  }, []);

  const parsedReports = useMemo(() => {
    if (metricsState.status !== "success") {
      return [];
    }

    return Object.entries(metricsState.data).map(([reportName, reportText]) => {
      const metrics = parseReportMetrics(reportText);
      const ordered = ORDEN.filter((k) => k in metrics).map((k) => ({
        key: k,
        value: metrics[k]
      }));
      return { ordered, reportName, reportText, ...friendlyReport(reportName) };
    });
  }, [metricsState]);

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-950">
      <section className="mx-auto grid w-full max-w-5xl gap-8">
        <div>
          <p className="mb-3 text-sm font-medium uppercase tracking-wide text-emerald-700">
            NHANES Longevity
          </p>
          <h1 className="text-4xl font-semibold leading-tight sm:text-5xl">
            ¿Qué tan buenos son los modelos?
          </h1>
        </div>

        {/* Explicacion para gente que no sabe de ML */}
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 text-sm leading-6 text-emerald-950">
          <p className="font-semibold">En simple 👇</p>
          <p className="mt-1">
            Entrenamos <strong>tres modelos</strong> de inteligencia artificial con
            datos reales de <strong>~42.000 adultos</strong> de la encuesta NHANES
            (EE. UU., 7 ciclos): tu <strong>edad biológica</strong>, tu{" "}
            <strong>parecido con un perfil 70+</strong> y tu{" "}
            <strong>riesgo de mortalidad a 10 años</strong>. Cada modelo usa la porción
            de esos datos que le corresponde. Aquí te mostramos qué tan bien funcionan,
            sin tecnicismos.
          </p>
          <p className="mt-2 text-emerald-800">
            Las <strong>barras</strong> van de 0 a 100%: cuanto más llenas y
            verdes, mejor. Los valores son sobre datos que los modelos{" "}
            <strong>nunca vieron</strong> al entrenar (su «examen final»).
          </p>
        </div>

        {metricsState.status === "loading" && (
          <div className="rounded-md border border-slate-200 bg-white p-6 text-sm text-slate-600">
            Cargando métricas...
          </div>
        )}

        {metricsState.status === "error" && (
          <div className="rounded-md border border-red-200 bg-red-50 p-6 text-sm text-red-800">
            <p className="font-medium">No se pudieron cargar las métricas</p>
            <p className="mt-2">Revisa que la API esté disponible en {METRICS_URL}.</p>
            <p className="mt-2 text-xs">{metricsState.error}</p>
          </div>
        )}

        {metricsState.status === "success" &&
          parsedReports.map(
            ({ ordered, reportName, reportText, titulo, subtitulo }) => (
              <section
                className="grid gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
                key={reportName}
              >
                <div>
                  <h2 className="text-xl font-semibold text-slate-950">{titulo}</h2>
                  {subtitulo && (
                    <p className="mt-1 text-sm text-slate-500">{subtitulo}</p>
                  )}
                </div>

                {ordered.length > 0 ? (
                  <div className="grid gap-4 sm:grid-cols-2">
                    {ordered.map(({ key, value }) => (
                      <MetricCard
                        key={`${reportName}-${key}`}
                        metricKey={key}
                        value={value}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                    No se detectaron métricas numéricas en este reporte.
                  </div>
                )}

                {/* El reporte tecnico crudo, para quien lo quiera, colapsado */}
                <details className="group rounded-md border border-slate-200 bg-slate-50">
                  <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium text-slate-600 hover:text-slate-900">
                    Ver reporte técnico completo
                  </summary>
                  <pre className="overflow-auto rounded-b-md bg-slate-950 p-4 text-xs leading-6 text-slate-50">
                    {reportText}
                  </pre>
                </details>
              </section>
            )
          )}
      </section>
    </main>
  );
}
