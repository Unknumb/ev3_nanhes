// Parseo de los reportes de texto que devuelve GET /metrics.
// Lo usan la pagina tecnica (/metrics) y el componente ModelStats de la landing.

export type ParsedMetric = { name: string; value: string };

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

export function normalizeMetricName(name: string) {
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

export function extractMetrics(reportText: string): ParsedMetric[] {
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

// Parser robusto orientado al formato de los reportes del equipo. A diferencia
// de extractMetrics, tolera texto entre la etiqueta y el numero (p. ej.
// "Accuracy (test):     0.9072"), reconoce "R²" y PREFIERE los valores de test
// sobre los de validacion cruzada ("Mejor ... (CV train)"). Devuelve numeros.
export type CanonicalMetric =
  | "accuracy"
  | "f1"
  | "precision"
  | "recall"
  | "roc_auc"
  | "mae"
  | "rmse"
  | "r2";

function canonicalFromLabel(label: string): CanonicalMetric | null {
  if (label.includes("accuracy")) return "accuracy";
  if (label.includes("roc") || label.includes("auc")) return "roc_auc";
  if (label.includes("f1")) return "f1";
  if (label.includes("precision")) return "precision";
  if (label.includes("recall")) return "recall";
  if (label.includes("rmse")) return "rmse";
  if (label.includes("mae")) return "mae";
  if (label.includes("r²") || label.includes("r2")) return "r2";
  return null;
}

export function parseReportMetrics(reportText: string): Record<string, number> {
  // prioridad: test (2) > simple (1) > CV/“mejor” (0). Solo sobrescribe si mejora.
  const best: Record<string, { value: number; prio: number }> = {};

  for (const rawLine of reportText.split("\n")) {
    const line = rawLine.trim();
    const match = line.match(/^(.+?)[:=]\s*(-?\d+(?:\.\d+)?)/);
    if (!match) continue;

    const label = match[1].toLowerCase();
    const key = canonicalFromLabel(label);
    if (!key) continue;

    const value = Number.parseFloat(match[2]);
    if (!Number.isFinite(value)) continue;

    const prio = label.includes("test")
      ? 2
      : label.includes("cv") || label.includes("mejor")
        ? 0
        : 1;

    if (!(key in best) || prio >= best[key].prio) {
      best[key] = { value, prio };
    }
  }

  return Object.fromEntries(
    Object.entries(best).map(([key, { value }]) => [key, value])
  );
}

// Busca una metrica por nombre dentro de TODOS los reportes (devuelve el primer match).
export function findMetric(
  reports: Record<string, string>,
  metricName: string
): string | null {
  for (const text of Object.values(reports)) {
    const match = extractMetrics(text).find((m) => m.name === metricName);
    if (match) {
      return match.value;
    }
  }
  return null;
}
