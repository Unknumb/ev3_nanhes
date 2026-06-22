"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { FEATURE_IMPORTANCE_URL, fetchWithTimeout } from "@/lib/api";

type Importance = {
  feature: string;
  label: string;
  importance: number;
  pct: number;
};

type ImportanceResponse = {
  model: string;
  clinical_only: boolean;
  importancias: Importance[];
};

export function GlobalImportanceChart({
  clinicalOnly = true,
  model = "clasificacion",
  topN = 7
}: {
  clinicalOnly?: boolean;
  model?: "clasificacion" | "regresion";
  topN?: number;
}) {
  const [data, setData] = useState<Importance[] | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      try {
        const url = `${FEATURE_IMPORTANCE_URL}?top_n=${topN}&model=${model}&clinical_only=${clinicalOnly}`;
        const response = await fetchWithTimeout(url);
        if (!response.ok) {
          return;
        }
        const body = (await response.json()) as ImportanceResponse;
        if (isMounted) {
          setData(body.importancias);
        }
      } catch {
        // silencioso: la landing funciona aunque no haya importancias
      }
    }

    load();

    return () => {
      isMounted = false;
    };
  }, [clinicalOnly, model, topN]);

  const chartData = useMemo(
    () =>
      (data ?? []).map((item) => ({
        label: item.label.replace(/\s*\(.*\)\s*/, ""),
        pct: item.pct
      })),
    [data]
  );

  if (!data || data.length === 0) {
    return null;
  }

  return (
    <section className="grid gap-4 rounded-md border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <h2 className="text-2xl font-semibold text-slate-950">
          Qué biomarcadores pesan más
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Peso relativo de cada biomarcador en el modelo de longevidad (entre los
          marcadores clínicos). Tras calcular tu resultado verás el detalle SHAP de tu
          caso particular.
        </p>
      </div>

      <div className="h-80 w-full">
        <ResponsiveContainer height="100%" width="100%">
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ left: 16, right: 32 }}
          >
            <CartesianGrid horizontal={false} strokeDasharray="3 3" />
            <XAxis type="number" tick={{ fontSize: 12 }} unit="%" />
            <YAxis
              dataKey="label"
              type="category"
              tick={{ fontSize: 12 }}
              width={150}
            />
            <Tooltip formatter={(value) => [`${value}%`, "Peso"]} />
            <Bar dataKey="pct" fill="#047857" radius={[0, 4, 4, 0]}>
              <LabelList
                dataKey="pct"
                formatter={(value) => `${value}%`}
                position="right"
                style={{ fontSize: 12, fill: "#334155" }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
