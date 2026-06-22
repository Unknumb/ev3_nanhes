"use client";

import { useEffect, useState } from "react";
import { METRICS_URL, fetchWithTimeout } from "@/lib/api";
import { findMetric } from "@/lib/metrics";

type StatCard = {
  value: string;
  title: string;
  blurb: string;
};

function buildCards(reports: Record<string, string>): StatCard[] {
  const accuracy = findMetric(reports, "accuracy");
  const f1 = findMetric(reports, "f1");
  const mae = findMetric(reports, "mae");
  const r2 = findMetric(reports, "r2");

  const cards: StatCard[] = [];

  if (accuracy) {
    const pct = Math.round(Number(accuracy) * 100);
    cards.push({
      value: `${pct}%`,
      title: "Acierta la longevidad",
      blurb: "de las veces clasifica bien si alguien vivirá 70+ años."
    });
  }

  if (mae) {
    cards.push({
      value: `±${Math.round(Number(mae))} años`,
      title: "Error de edad biológica",
      blurb: "diferencia promedio entre la edad estimada y la real."
    });
  }

  if (r2) {
    const pct = Math.round(Number(r2) * 100);
    cards.push({
      value: `${pct}%`,
      title: "Variabilidad explicada",
      blurb: "del envejecimiento queda capturado por el modelo."
    });
  }

  if (f1 && cards.length < 4) {
    cards.push({
      value: Number(f1).toFixed(2),
      title: "Balance (F1)",
      blurb: "equilibrio entre precisión y cobertura del clasificador."
    });
  }

  return cards;
}

export function ModelStats() {
  const [cards, setCards] = useState<StatCard[] | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      try {
        const response = await fetchWithTimeout(METRICS_URL);
        if (!response.ok) {
          return;
        }
        const reports = (await response.json()) as Record<string, string>;
        if (isMounted) {
          setCards(buildCards(reports));
        }
      } catch {
        // silencioso: la landing funciona aunque no haya métricas
      }
    }

    load();

    return () => {
      isMounted = false;
    };
  }, []);

  if (!cards || cards.length === 0) {
    return null;
  }

  return (
    <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {cards.map((card) => (
        <div
          className="rounded-md border border-slate-200 bg-white p-5 shadow-sm"
          key={card.title}
        >
          <p className="text-3xl font-semibold text-emerald-700">{card.value}</p>
          <p className="mt-2 text-sm font-semibold text-slate-950">{card.title}</p>
          <p className="mt-1 text-sm text-slate-600">{card.blurb}</p>
        </div>
      ))}
    </section>
  );
}
