"use client";

import { useEffect, useState } from "react";
import { AGGREGATES_URL, fetchWithTimeout } from "@/lib/api";

export function SocialProof() {
  const [total, setTotal] = useState<number | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      try {
        const response = await fetchWithTimeout(AGGREGATES_URL);
        if (!response.ok) {
          return;
        }
        const body = (await response.json()) as { total_predicciones: number };
        if (isMounted && body.total_predicciones > 0) {
          setTotal(body.total_predicciones);
        }
      } catch {
        // silencioso
      }
    }

    load();

    return () => {
      isMounted = false;
    };
  }, []);

  if (total === null) {
    return null;
  }

  return (
    <p className="text-sm font-medium text-emerald-700">
      <span className="font-semibold">{total.toLocaleString("es-CL")}</span> personas
      ya estimaron su edad biológica.
    </p>
  );
}
