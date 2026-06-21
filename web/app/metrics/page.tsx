"use client";

import { useEffect, useMemo, useState } from "react";
import { METRICS_URL, fetchWithTimeout, getFetchErrorMessage } from "@/lib/api";

type MetricsResponse = Record<string, string>;

type MetricsState =
  | { status: "loading"; data: null; error: null }
  | { status: "success"; data: MetricsResponse; error: null }
  | { status: "error"; data: null; error: string };

const metricLabels = [
  "accuracy",
  "precision",
  "recall",
  "f1",
  "f1-score",
  "roc_auc",
  "roc auc",
  "auc",
  "mae",
  "mse",
  "rmse",
  "r2",
  "r2_score"
];

function normalizeMetricName(name: string) {
  const normalized = name.toLowerCase().replace(/[-\s]+/g, "_");

  if (normalized === "f1_score") {
    return "f1";
  }

  if (normalized === "roc_auc" || normalized === "rocauc") {
    return "roc_auc";
  }

  if (normalized === "r2_score") {
    return "r2";
  }

  return normalized;
}

function extractMetrics(reportText: string) {
  const found = new Map<string, string>();

  metricLabels.forEach((label) => {
    const pattern = new RegExp(
      `\\b${label.replace(/[-_\s]+/g, "[-_\\s]*")}\\b\\s*[:=]?\\s*(-?\\d+(?:\\.\\d+)?)`,
      "i"
    );
    const match = reportText.match(pattern);

    if (match?.[1]) {
      found.set(normalizeMetricName(label), match[1]);
    }
  });

  return Array.from(found.entries()).map(([name, value]) => ({ name, value }));
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

    return Object.entries(metricsState.data).map(([reportName, reportText]) => ({
      metrics: extractMetrics(reportText),
      reportName,
      reportText
    }));
  }, [metricsState]);

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-950">
      <section className="mx-auto grid w-full max-w-5xl gap-8">
        <div>
          <p className="mb-3 text-sm font-medium uppercase tracking-wide text-emerald-700">
            NHANES Longevity
          </p>
          <h1 className="text-4xl font-semibold leading-tight sm:text-5xl">
            Métricas del modelo
          </h1>
        </div>

        {metricsState.status === "loading" && (
          <div className="rounded-md border border-slate-200 bg-white p-6 text-sm text-slate-600">
            Cargando métricas...
          </div>
        )}

        {metricsState.status === "error" && (
          <div className="rounded-md border border-red-200 bg-red-50 p-6 text-sm text-red-800">
            <p className="font-medium">No se pudieron cargar las métricas</p>
            <p className="mt-2">
              Revisa que la API esté disponible en {METRICS_URL}.
            </p>
            <p className="mt-2 text-xs">{metricsState.error}</p>
          </div>
        )}

        {metricsState.status === "success" && (
          <div className="grid gap-6">
            {parsedReports.map(({ metrics, reportName, reportText }) => (
              <section
                className="grid gap-4 rounded-md border border-slate-200 bg-white p-5"
                key={reportName}
              >
                <h2 className="text-xl font-semibold text-slate-950">
                  {reportName}
                </h2>

                {metrics.length > 0 ? (
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    {metrics.map((metric) => (
                      <div
                        className="rounded-md border border-slate-200 bg-slate-50 p-4"
                        key={`${reportName}-${metric.name}`}
                      >
                        <p className="text-xs font-medium uppercase text-slate-500">
                          {metric.name}
                        </p>
                        <p className="mt-2 text-2xl font-semibold text-slate-950">
                          {metric.value}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                    No se detectaron métricas numéricas estructuradas en este
                    reporte.
                  </div>
                )}

                <pre className="overflow-auto rounded-md bg-slate-950 p-4 text-xs leading-6 text-slate-50">
                  {reportText}
                </pre>
              </section>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
