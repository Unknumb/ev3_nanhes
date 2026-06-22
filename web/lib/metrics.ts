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
