"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { AGGREGATES_URL } from "@/lib/api";

type DistributionBin = {
  min: number;
  max: number;
  count: number;
};

type RecentPrediction = {
  created_at: string;
  es_longevo: boolean;
  probabilidad: number;
  edad_biologica: number;
  gap: number | null;
};

type AggregatesResponse = {
  total_predicciones: number;
  pct_longevos: number | null;
  edad_biologica_promedio: number | null;
  gap_promedio: number | null;
  edad_biologica_distribucion: DistributionBin[];
  ultimas: RecentPrediction[];
};

type AggregatesState =
  | { status: "loading"; data: null; error: null }
  | { status: "success"; data: AggregatesResponse; error: null }
  | { status: "error"; data: null; error: string };

function formatNumber(value: number | null, suffix = "") {
  if (value === null) {
    return "Sin datos";
  }

  return `${value}${suffix}`;
}

function formatProbability(value: number) {
  const percent = value <= 1 ? value * 100 : value;
  return `${Math.round(percent)}%`;
}

function formatDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("es-CL", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(date);
}

function KpiCard({
  label,
  value
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-3 text-3xl font-semibold text-slate-950">{value}</p>
    </div>
  );
}

export default function ExecutivePage() {
  const [aggregatesState, setAggregatesState] = useState<AggregatesState>({
    status: "loading",
    data: null,
    error: null
  });

  useEffect(() => {
    let isMounted = true;

    async function loadAggregates() {
      try {
        const response = await fetch(AGGREGATES_URL);

        if (!response.ok) {
          throw new Error(`La API respondió ${response.status} al cargar agregados`);
        }

        const aggregates = (await response.json()) as AggregatesResponse;

        if (isMounted) {
          setAggregatesState({
            status: "success",
            data: aggregates,
            error: null
          });
        }
      } catch (error) {
        if (isMounted) {
          setAggregatesState({
            status: "error",
            data: null,
            error:
              error instanceof Error
                ? error.message
                : "No se pudo cargar la vista ejecutiva"
          });
        }
      }
    }

    loadAggregates();

    return () => {
      isMounted = false;
    };
  }, []);

  const chartData = useMemo(() => {
    if (aggregatesState.status !== "success") {
      return [];
    }

    return aggregatesState.data.edad_biologica_distribucion.map((bin) => ({
      count: bin.count,
      range: `${bin.min}-${bin.max}`
    }));
  }, [aggregatesState]);

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-950">
      <section className="mx-auto grid w-full max-w-5xl gap-8">
        <div>
          <p className="mb-3 text-sm font-medium uppercase tracking-wide text-emerald-700">
            NHANES Longevity
          </p>
          <h1 className="text-4xl font-semibold leading-tight sm:text-5xl">
            Vista ejecutiva
          </h1>
          <p className="mt-4 text-lg leading-8 text-slate-700">
            Resumen del historial de predicciones registradas por la API.
          </p>
        </div>

        {aggregatesState.status === "loading" && (
          <div className="rounded-md border border-slate-200 bg-white p-6 text-sm text-slate-600">
            Cargando vista ejecutiva...
          </div>
        )}

        {aggregatesState.status === "error" && (
          <div className="rounded-md border border-red-200 bg-red-50 p-6 text-sm text-red-800">
            <p className="font-medium">No se pudo cargar la vista ejecutiva</p>
            <p className="mt-2">
              Revisa que la API esté disponible en {AGGREGATES_URL}.
            </p>
            <p className="mt-2 text-xs">{aggregatesState.error}</p>
          </div>
        )}

        {aggregatesState.status === "success" &&
          aggregatesState.data.total_predicciones === 0 && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-6 text-amber-900">
              Aún no hay predicciones registradas. Ejecuta predicciones desde la
              vista operativa para poblar el historial ejecutivo.
            </div>
          )}

        {aggregatesState.status === "success" &&
          aggregatesState.data.total_predicciones > 0 && (
            <div className="grid gap-8">
              <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <KpiCard
                  label="Total de predicciones"
                  value={aggregatesState.data.total_predicciones}
                />
                <KpiCard
                  label="% longevos"
                  value={formatNumber(aggregatesState.data.pct_longevos, "%")}
                />
                <KpiCard
                  label="Edad biológica promedio"
                  value={formatNumber(
                    aggregatesState.data.edad_biologica_promedio,
                    " años"
                  )}
                />
                <KpiCard
                  label="Gap promedio"
                  value={formatNumber(aggregatesState.data.gap_promedio, " años")}
                />
              </section>

              <section className="grid gap-4 rounded-md border border-slate-200 bg-white p-6 shadow-sm">
                <div>
                  <h2 className="text-2xl font-semibold text-slate-950">
                    Distribución de edad biológica
                  </h2>
                  <p className="mt-2 text-sm text-slate-600">
                    Histograma de predicciones históricas agrupadas por rango.
                  </p>
                </div>

                <div className="h-80 w-full">
                  <ResponsiveContainer height="100%" width="100%">
                    <BarChart data={chartData} margin={{ left: 8, right: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="range" tick={{ fontSize: 12 }} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                      <Tooltip />
                      <Bar dataKey="count" fill="#047857" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </section>

              <section className="grid gap-4 rounded-md border border-slate-200 bg-white p-6 shadow-sm">
                <div>
                  <h2 className="text-2xl font-semibold text-slate-950">
                    Últimas predicciones
                  </h2>
                  <p className="mt-2 text-sm text-slate-600">
                    Registros más recientes almacenados en la base de datos.
                  </p>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-600">
                        <th className="py-3 pr-4 font-semibold">Fecha</th>
                        <th className="py-3 pr-4 font-semibold">Longevo</th>
                        <th className="py-3 pr-4 font-semibold">Probabilidad</th>
                        <th className="py-3 pr-4 font-semibold">Edad biológica</th>
                        <th className="py-3 pr-4 font-semibold">Gap</th>
                      </tr>
                    </thead>
                    <tbody>
                      {aggregatesState.data.ultimas.map((prediction) => (
                        <tr
                          className="border-b border-slate-100"
                          key={`${prediction.created_at}-${prediction.probabilidad}`}
                        >
                          <td className="py-3 pr-4 text-slate-700">
                            {formatDate(prediction.created_at)}
                          </td>
                          <td className="py-3 pr-4">
                            <span
                              className={
                                prediction.es_longevo
                                  ? "rounded-md bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-800"
                                  : "rounded-md bg-red-100 px-2 py-1 text-xs font-semibold text-red-800"
                              }
                            >
                              {prediction.es_longevo ? "Sí" : "No"}
                            </span>
                          </td>
                          <td className="py-3 pr-4 text-slate-700">
                            {formatProbability(prediction.probabilidad)}
                          </td>
                          <td className="py-3 pr-4 text-slate-700">
                            {prediction.edad_biologica} años
                          </td>
                          <td className="py-3 pr-4 text-slate-700">
                            {formatNumber(prediction.gap, " años")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          )}
      </section>
    </main>
  );
}
