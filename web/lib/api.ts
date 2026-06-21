export const NEXT_PUBLIC_API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const SCHEMA_URL = `${NEXT_PUBLIC_API_URL}/schema`;

export const PREDICT_URL = `${NEXT_PUBLIC_API_URL}/predict`;

export const EXPLAIN_URL = `${NEXT_PUBLIC_API_URL}/explain`;

export const METRICS_URL = `${NEXT_PUBLIC_API_URL}/metrics`;

export const AGGREGATES_URL = `${NEXT_PUBLIC_API_URL}/aggregates`;
