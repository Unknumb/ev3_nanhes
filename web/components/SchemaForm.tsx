"use client";

import { useEffect, useMemo, useState } from "react";
import {
  EXPLAIN_URL,
  PREDICT_URL,
  SCHEMA_URL,
  fetchWithTimeout,
  getFetchErrorMessage
} from "@/lib/api";

type SchemaOption = {
  value: number | string;
  label: string;
};

type SchemaField = {
  code: string;
  label: string;
  type: "numeric" | "categorical";
  required: boolean;
  group: string;
  unit?: string;
  min?: number;
  max?: number;
  note?: string;
  options?: SchemaOption[];
};

type FeatureSchema = {
  cycle?: string;
  description?: string;
  features: SchemaField[];
  extra_inputs?: SchemaField[] | Record<string, SchemaField>;
};

type PredictPayload = {
  features: Record<string, number | string | null>;
  edad_cronologica: number | null;
};

type PredictResult = {
  es_longevo: boolean;
  probabilidad: number;
  edad_biologica: number;
  edad_cronologica: number | null;
  gap: number | null;
};

type SubmitState =
  | { status: "idle"; message: null }
  | { status: "submitting"; message: null }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

type ExplainContribution = {
  feature: string;
  shap: number;
  empuja: "longevo" | "no_longevo";
};

type ExplainResult = {
  base_value?: number;
  contribuciones: ExplainContribution[];
};

type ExplainState =
  | { status: "idle"; message: null }
  | { status: "loading"; message: string }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

type SchemaState =
  | { status: "loading"; data: null; error: null }
  | { status: "loaded"; data: FeatureSchema; error: null }
  | { status: "error"; data: null; error: string };

function normalizeExtraInputs(
  extraInputs: FeatureSchema["extra_inputs"]
): SchemaField[] {
  if (!extraInputs) {
    return [];
  }

  return Array.isArray(extraInputs) ? extraInputs : Object.values(extraInputs);
}

function groupFields(fields: SchemaField[]) {
  return fields.reduce<Record<string, SchemaField[]>>((groups, field) => {
    const groupName = field.group || "Otros";
    groups[groupName] = [...(groups[groupName] ?? []), field];
    return groups;
  }, {});
}

function parseFieldValue(field: SchemaField, formData: FormData) {
  const rawValue = formData.get(field.code);

  if (rawValue === null || rawValue === "") {
    return null;
  }

  if (field.type === "numeric") {
    return Number(rawValue);
  }

  const matchingOption = field.options?.find(
    (option) => String(option.value) === String(rawValue)
  );

  if (typeof matchingOption?.value === "number") {
    return Number(rawValue);
  }

  return String(rawValue);
}

function buildPredictPayload(
  schema: FeatureSchema,
  formData: FormData
): PredictPayload {
  const features = schema.features.reduce<Record<string, number | string | null>>(
    (payloadFeatures, field) => {
      payloadFeatures[field.code] = parseFieldValue(field, formData);
      return payloadFeatures;
    },
    {}
  );

  const edadCronologicaField = normalizeExtraInputs(schema.extra_inputs).find(
    (field) => field.code === "edad_cronologica"
  );

  return {
    features,
    edad_cronologica: edadCronologicaField
      ? (parseFieldValue(edadCronologicaField, formData) as number | null)
      : null
  };
}

function getErrorsByField(detail: unknown) {
  const errorsByField: Record<string, string> = {};

  if (Array.isArray(detail)) {
    detail.forEach((item) => {
      const message =
        typeof item === "string"
          ? item
          : typeof item === "object" && item !== null && "msg" in item
            ? String(item.msg)
            : JSON.stringify(item);
      const match = message.match(/'([^']+)'/);

      if (match?.[1]) {
        errorsByField[match[1]] = message;
      }
    });
  }

  return errorsByField;
}

function formatYears(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "No disponible";
  }

  return `${Math.round(value)} años`;
}

function formatGap(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "No disponible";
  }

  const rounded = Math.round(value * 10) / 10;
  const sign = rounded > 0 ? "+" : "";

  return `${sign}${rounded} años`;
}

function getProbabilityPercent(probability: number) {
  return probability <= 1 ? probability * 100 : probability;
}

function getProbabilityTone(percent: number) {
  if (percent > 70) {
    return {
      badge: "bg-emerald-100 text-emerald-800",
      bar: "bg-emerald-600",
      border: "border-emerald-200",
      label: "Alta"
    };
  }

  if (percent >= 40) {
    return {
      badge: "bg-amber-100 text-amber-900",
      bar: "bg-amber-500",
      border: "border-amber-200",
      label: "Media"
    };
  }

  return {
    badge: "bg-red-100 text-red-800",
    bar: "bg-red-600",
    border: "border-red-200",
    label: "Baja"
  };
}

function getGapLabel(gap: number | null) {
  if (gap === null) {
    return "Gap";
  }

  if (gap > 0) {
    return "Envejecimiento acelerado";
  }

  if (gap < 0) {
    return "Envejecimiento menor al cronológico";
  }

  return "Edad biológica alineada";
}

function ResultSummary({ result }: { result: PredictResult }) {
  const probabilityPercent = getProbabilityPercent(result.probabilidad);
  const clampedPercent = Math.max(0, Math.min(100, probabilityPercent));
  const tone = getProbabilityTone(probabilityPercent);

  return (
    <section
      className={`grid gap-6 rounded-md border ${tone.border} bg-white p-6 shadow-sm`}
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-slate-500">
            Resultado
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-950">
            Evaluación de longevidad
          </h2>
        </div>
        <span
          className={`w-fit rounded-md px-3 py-1 text-sm font-semibold ${tone.badge}`}
        >
          Probabilidad {tone.label}
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm text-slate-500">Edad cronológica</p>
          <p className="mt-2 text-2xl font-semibold text-slate-950">
            {formatYears(result.edad_cronologica)}
          </p>
        </div>
        <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm text-slate-500">Edad biológica</p>
          <p className="mt-2 text-2xl font-semibold text-slate-950">
            {formatYears(result.edad_biologica)}
          </p>
        </div>
        <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm text-slate-500">{getGapLabel(result.gap)}</p>
          <p className="mt-2 text-2xl font-semibold text-slate-950">
            {formatGap(result.gap)}
          </p>
        </div>
      </div>

      <div className="grid gap-3">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-sm text-slate-500">Probabilidad de longevidad</p>
            <p className="mt-1 text-5xl font-semibold text-slate-950">
              {Math.round(probabilityPercent)}%
            </p>
          </div>
          <p className="pb-1 text-sm font-medium text-slate-600">
            {result.es_longevo ? "Clasifica como longevo" : "No clasifica como longevo"}
          </p>
        </div>
        <div className="h-4 overflow-hidden rounded-md bg-slate-200">
          <div
            className={`h-full rounded-md ${tone.bar}`}
            style={{ width: `${clampedPercent}%` }}
          />
        </div>
      </div>
    </section>
  );
}

function ShapBars({ explainResult }: { explainResult: ExplainResult }) {
  const maxMagnitude = Math.max(
    ...explainResult.contribuciones.map((contribution) =>
      Math.abs(contribution.shap)
    ),
    0
  );

  return (
    <section className="grid gap-5 rounded-md border border-slate-200 bg-white p-6 shadow-sm">
      <div>
          <p className="text-sm font-medium uppercase tracking-wide text-slate-500">
            SHAP
          </p>
        <h2 className="mt-2 text-2xl font-semibold text-slate-950">
          Factores que más influyen
        </h2>
      </div>

      <div className="grid gap-4">
        {explainResult.contribuciones.map((contribution) => {
          const magnitude = Math.abs(contribution.shap);
          const width =
            maxMagnitude > 0 ? Math.max(6, (magnitude / maxMagnitude) * 100) : 0;
          const isPositive = contribution.empuja === "longevo";

          return (
            <div className="grid gap-2" key={`${contribution.feature}-${contribution.shap}`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium text-slate-950">
                  {contribution.feature}
                </span>
                <span
                  className={
                    isPositive
                      ? "rounded-md bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-800"
                      : "rounded-md bg-red-100 px-2 py-1 text-xs font-semibold text-red-800"
                  }
                >
                  {isPositive ? "Empuja a longevo" : "Empuja a no longevo"}
                </span>
              </div>
              <div className="grid grid-cols-[88px_1fr_72px] items-center gap-3">
                <span className="text-sm text-slate-500">
                  {magnitude.toFixed(4)}
                </span>
                <div className="h-3 overflow-hidden rounded-md bg-slate-200">
                  <div
                    className={
                      isPositive
                        ? "h-full rounded-md bg-emerald-600"
                        : "h-full rounded-md bg-red-600"
                    }
                    style={{ width: `${width}%` }}
                  />
                </div>
                <span className="text-right text-sm text-slate-500">
                  {contribution.shap > 0 ? "+" : ""}
                  {contribution.shap}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function TechnicalJson({
  explainResult,
  lastPayload,
  predictResult
}: {
  explainResult: ExplainResult | null;
  lastPayload: PredictPayload | null;
  predictResult: PredictResult | null;
}) {
  return (
    <details className="rounded-md border border-slate-200 bg-white p-5">
      <summary className="cursor-pointer text-sm font-semibold text-slate-700">
        Ver JSON técnico
      </summary>
      <div className="mt-4 grid gap-4">
        {lastPayload && (
          <div className="grid gap-2">
            <h3 className="text-sm font-semibold text-slate-700">
              Payload enviado
            </h3>
            <pre className="overflow-auto rounded-md bg-slate-950 p-4 text-xs leading-6 text-slate-50">
              {JSON.stringify(lastPayload, null, 2)}
            </pre>
          </div>
        )}

        {predictResult && (
          <div className="grid gap-2">
            <h3 className="text-sm font-semibold text-slate-700">
              Respuesta de /predict
            </h3>
            <pre className="overflow-auto rounded-md bg-slate-950 p-4 text-xs leading-6 text-slate-50">
              {JSON.stringify(predictResult, null, 2)}
            </pre>
          </div>
        )}

        {explainResult && (
          <div className="grid gap-2">
            <h3 className="text-sm font-semibold text-slate-700">
              Respuesta de /explain
            </h3>
            <pre className="overflow-auto rounded-md bg-slate-950 p-4 text-xs leading-6 text-slate-50">
              {JSON.stringify(explainResult, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </details>
  );
}

function FieldControl({
  error,
  field
}: {
  error?: string;
  field: SchemaField;
}) {
  const fieldId = `field-${field.code}`;

  return (
    <label
      className="grid gap-2 rounded-md border border-slate-200 bg-white p-4"
      htmlFor={fieldId}
    >
      <span className="flex items-start justify-between gap-3">
        <span>
          <span className="block text-sm font-medium text-slate-950">
            {field.label}
          </span>
          <span className="mt-1 block text-xs text-slate-500">{field.code}</span>
        </span>
        {!field.required && (
          <span className="shrink-0 text-xs font-medium text-slate-500">
            Opcional
          </span>
        )}
      </span>

      {field.type === "numeric" ? (
        <div className="flex items-center gap-3">
          <input
            className="min-h-11 w-full rounded-md border border-slate-300 px-3 text-sm outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
            id={fieldId}
            max={field.max}
            min={field.min}
            name={field.code}
            placeholder={
              field.min !== undefined && field.max !== undefined
                ? `${field.min} - ${field.max}`
                : undefined
            }
            required={field.required}
            type="number"
          />
          {field.unit && (
            <span className="min-w-14 text-sm text-slate-600">{field.unit}</span>
          )}
        </div>
      ) : (
        <select
          className="min-h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
          id={fieldId}
          name={field.code}
          required={field.required}
        >
          <option value="">Seleccionar</option>
          {(field.options ?? []).map((option) => (
            <option key={String(option.value)} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      )}

      {field.note && <span className="text-xs text-slate-500">{field.note}</span>}
      {error && <span className="text-xs font-medium text-red-700">{error}</span>}
    </label>
  );
}

export function SchemaForm() {
  const [schemaState, setSchemaState] = useState<SchemaState>({
    status: "loading",
    data: null,
    error: null
  });
  const [submitState, setSubmitState] = useState<SubmitState>({
    status: "idle",
    message: null
  });
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [lastPayload, setLastPayload] = useState<PredictPayload | null>(null);
  const [predictResult, setPredictResult] = useState<PredictResult | null>(null);
  const [explainState, setExplainState] = useState<ExplainState>({
    status: "idle",
    message: null
  });
  const [explainResult, setExplainResult] = useState<ExplainResult | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadSchema() {
      try {
        const response = await fetchWithTimeout(SCHEMA_URL);

        if (!response.ok) {
          throw new Error(`La API respondió ${response.status} al cargar el formulario`);
        }

        const schema = (await response.json()) as FeatureSchema;

        if (isMounted) {
          setSchemaState({ status: "loaded", data: schema, error: null });
        }
      } catch (error) {
        if (isMounted) {
          setSchemaState({
            status: "error",
            data: null,
            error:
              error instanceof Error
                ? getFetchErrorMessage(error, "No se pudo cargar el formulario")
                : "No se pudo cargar el formulario"
          });
        }
      }
    }

    loadSchema();

    return () => {
      isMounted = false;
    };
  }, []);

  const featureGroups = useMemo(() => {
    if (schemaState.status !== "loaded") {
      return {};
    }

    return groupFields(schemaState.data.features);
  }, [schemaState]);

  const edadCronologica = useMemo(() => {
    if (schemaState.status !== "loaded") {
      return undefined;
    }

    return normalizeExtraInputs(schemaState.data.extra_inputs).find(
      (field) => field.code === "edad_cronologica"
    );
  }, [schemaState]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (schemaState.status !== "loaded") {
      return;
    }

    const formData = new FormData(event.currentTarget);
    const payload = buildPredictPayload(schemaState.data, formData);

    setFieldErrors({});
    setLastPayload(payload);
    setPredictResult(null);
    setExplainResult(null);
    setExplainState({ status: "idle", message: null });
    setSubmitState({ status: "submitting", message: null });

    try {
      const response = await fetchWithTimeout(PREDICT_URL, {
        body: JSON.stringify(payload),
        headers: {
          "Content-Type": "application/json"
        },
        method: "POST"
      });
      const responseBody = await response.json().catch(() => null);

      if (!response.ok) {
        if (response.status === 422) {
          const errors = getErrorsByField(responseBody?.detail);
          setFieldErrors(errors);
          throw new Error("Revisa los campos marcados por la API");
        }

        if (response.status === 503) {
          throw new Error("Modelo no disponible actualmente");
        }

        throw new Error(
          responseBody?.detail
            ? String(responseBody.detail)
            : `La API respondió ${response.status} al calcular la predicción`
        );
      }

      setPredictResult(responseBody as PredictResult);
      setSubmitState({
        status: "success",
        message: "Predicción recibida correctamente"
      });
      setExplainState({
        status: "loading",
        message: "Cargando explicación SHAP"
      });

      try {
        const explainResponse = await fetchWithTimeout(EXPLAIN_URL, {
          body: JSON.stringify(payload),
          headers: {
            "Content-Type": "application/json"
          },
          method: "POST"
        });
        const explainBody = await explainResponse.json().catch(() => null);

        if (!explainResponse.ok) {
          throw new Error(
            explainBody?.detail
              ? String(explainBody.detail)
              : `La API respondió ${explainResponse.status} al cargar la explicación`
          );
        }

        setExplainResult(explainBody as ExplainResult);
        setExplainState({
          status: "success",
          message: "Explicación cargada"
        });
      } catch (error) {
        setExplainState({
          status: "error",
          message:
            error instanceof Error
              ? getFetchErrorMessage(error, "No se pudo cargar la explicación")
              : "No se pudo cargar la explicación"
        });
      }
    } catch (error) {
      setSubmitState({
        status: "error",
        message:
          error instanceof Error
            ? getFetchErrorMessage(error, "No se pudo enviar el formulario")
            : "No se pudo enviar el formulario"
      });
    }
  }

  if (schemaState.status === "loading") {
    return (
      <div className="rounded-md border border-slate-200 bg-white p-6 text-sm text-slate-600">
        Cargando formulario...
      </div>
    );
  }

  if (schemaState.status === "error") {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-6 text-sm text-red-800">
        <p className="font-medium">No se pudo cargar el formulario</p>
        <p className="mt-2 text-xs">{schemaState.error}</p>
      </div>
    );
  }

  return (
    <form className="grid gap-8" onSubmit={handleSubmit}>
      {edadCronologica && (
        <section className="grid gap-4">
          <h2 className="text-xl font-semibold text-slate-950">Referencia</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <FieldControl
              error={fieldErrors[edadCronologica.code]}
              field={edadCronologica}
            />
          </div>
        </section>
      )}

      {Object.entries(featureGroups).map(([groupName, fields]) => (
        <section className="grid gap-4" key={groupName}>
          <h2 className="text-xl font-semibold text-slate-950">{groupName}</h2>
          <div className="grid gap-4 md:grid-cols-2">
            {fields.map((field) => (
              <FieldControl
                error={fieldErrors[field.code]}
                field={field}
                key={field.code}
              />
            ))}
          </div>
        </section>
      ))}

      <section className="grid gap-4 border-t border-slate-200 pt-6">
        <button
          className="min-h-11 w-full rounded-md bg-emerald-700 px-5 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-400 sm:w-fit"
          disabled={submitState.status === "submitting"}
          type="submit"
        >
          {submitState.status === "submitting" ? "Enviando..." : "Calcular predicción"}
        </button>

        {submitState.status === "success" && (
          <div className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-800">
            {submitState.message}
          </div>
        )}

        {submitState.status === "error" && (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-800">
            {submitState.message}
          </div>
        )}
      </section>

      {predictResult && (
        <section className="grid gap-6">
          <ResultSummary result={predictResult} />

          {explainState.status === "loading" && (
            <div className="rounded-md border border-slate-200 bg-white p-5 text-sm text-slate-700">
              Cargando explicación SHAP...
            </div>
          )}

          {explainState.status === "error" && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-5 text-sm font-medium text-amber-900">
              No se pudo cargar la explicación SHAP: {explainState.message}
            </div>
          )}

          {explainState.status === "success" && explainResult && (
            <ShapBars explainResult={explainResult} />
          )}

          <TechnicalJson
            explainResult={explainResult}
            lastPayload={lastPayload}
            predictResult={predictResult}
          />
        </section>
      )}
    </form>
  );
}
