"use client";

import { useEffect, useMemo, useState } from "react";
import { PREDICT_URL, SCHEMA_URL } from "@/lib/api";

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

type SubmitState =
  | { status: "idle"; message: null }
  | { status: "submitting"; message: null }
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
  const [predictResult, setPredictResult] = useState<unknown>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadSchema() {
      try {
        const response = await fetch(SCHEMA_URL);

        if (!response.ok) {
          throw new Error(`GET /schema respondio ${response.status}`);
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
                ? error.message
                : "No se pudo cargar el schema"
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
    setSubmitState({ status: "submitting", message: null });

    try {
      const response = await fetch(PREDICT_URL, {
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
            : `POST /predict respondio ${response.status}`
        );
      }

      setPredictResult(responseBody);
      setSubmitState({
        status: "success",
        message: "Prediccion recibida correctamente"
      });
    } catch (error) {
      setSubmitState({
        status: "error",
        message:
          error instanceof Error
            ? error.message
            : "No se pudo enviar el formulario"
      });
    }
  }

  if (schemaState.status === "loading") {
    return (
      <div className="rounded-md border border-slate-200 bg-white p-6 text-sm text-slate-600">
        loading schema
      </div>
    );
  }

  if (schemaState.status === "error") {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-6 text-sm text-red-800">
        <p className="font-medium">schema error</p>
        <p className="mt-2">{schemaState.error}</p>
      </div>
    );
  }

  return (
    <form className="grid gap-8" onSubmit={handleSubmit}>
      <div className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-800">
        Schema cargado correctamente
      </div>

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
          {submitState.status === "submitting" ? "Enviando..." : "Enviar a predict"}
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

      {(lastPayload !== null || predictResult !== null) && (
        <section className="grid gap-4 rounded-md border border-slate-200 bg-white p-5">
          <h2 className="text-xl font-semibold text-slate-950">Resultado temporal</h2>

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

          {predictResult !== null && (
            <div className="grid gap-2">
              <h3 className="text-sm font-semibold text-slate-700">
                Respuesta de /predict
              </h3>
              <pre className="overflow-auto rounded-md bg-slate-950 p-4 text-xs leading-6 text-slate-50">
                {JSON.stringify(predictResult, null, 2)}
              </pre>
            </div>
          )}
        </section>
      )}
    </form>
  );
}
