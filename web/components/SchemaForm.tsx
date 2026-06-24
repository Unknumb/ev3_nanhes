"use client";

import { useEffect, useMemo, useState } from "react";
import {
  EXPLAIN_URL,
  MORTALITY_URL,
  PREDICT_URL,
  REPORT_URL,
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
  tier?: "essential" | "advanced";
  derived?: boolean;
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

type MortalityResult = {
  riesgo_10y: number;
  riesgo_pct: number;
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

type ReportResult = {
  html: string;
  pdf_base64: string | null;
  emailed: boolean;
  email_mode: string;
  guardado: boolean;
};

type ReportState =
  | { status: "idle"; message: null }
  | { status: "loading"; message: null }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

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

// Separa los campos en esenciales (visibles) y avanzados (acordeon). Los campos
// `derived` (p. ej. IMC) no se piden: se calculan en buildPredictPayload.
function partitionByTier(fields: SchemaField[]) {
  const inputs = fields.filter((field) => !field.derived);
  return {
    essential: inputs.filter((field) => field.tier !== "advanced"),
    advanced: inputs.filter((field) => field.tier === "advanced")
  };
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

// IMC = peso(kg) / estatura(m)^2. La estatura llega en cm desde el form.
function computeBmi(
  weightKg: number | string | null,
  heightCm: number | string | null
): number | null {
  const weight = typeof weightKg === "number" ? weightKg : Number(weightKg);
  const height = typeof heightCm === "number" ? heightCm : Number(heightCm);

  if (!weight || !height || Number.isNaN(weight) || Number.isNaN(height)) {
    return null;
  }

  const meters = height / 100;
  return Math.round((weight / (meters * meters)) * 10) / 10;
}

function buildPredictPayload(
  schema: FeatureSchema,
  formData: FormData
): PredictPayload {
  const features = schema.features.reduce<Record<string, number | string | null>>(
    (payloadFeatures, field) => {
      payloadFeatures[field.code] = field.derived
        ? null
        : parseFieldValue(field, formData);
      return payloadFeatures;
    },
    {}
  );

  // Campos derivados: el front los calcula y no los pide como input.
  if ("BMXBMI" in features) {
    features.BMXBMI = computeBmi(features.BMXWT, features.BMXHT);
  }

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

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

// Descarga el informe como PDF (decodifica el base64). Si la API no devolvió PDF
// (xhtml2pdf ausente), cae a HTML para no dejar al usuario sin informe.
function downloadReport(result: ReportResult) {
  if (result.pdf_base64) {
    const bytes = Uint8Array.from(atob(result.pdf_base64), (c) => c.charCodeAt(0));
    triggerDownload(new Blob([bytes], { type: "application/pdf" }), "informe-longevidad.pdf");
    return true;
  }
  triggerDownload(new Blob([result.html], { type: "text/html" }), "informe-longevidad.html");
  return false;
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

function getGapSentence(gap: number | null) {
  if (gap === null) {
    return "No ingresaste tu edad real, así que no podemos compararla.";
  }
  const años = Math.round(Math.abs(gap));
  if (gap > 1) {
    return `Tu cuerpo aparenta unos ${años} año(s) más que tu edad real.`;
  }
  if (gap < -1) {
    return `Tu cuerpo aparenta unos ${años} año(s) menos que tu edad real.`;
  }
  return "Tu edad biológica está alineada con tu edad real.";
}

function getSimilitudTexto(pct: number) {
  if (pct < 40) {
    return "Un valor bajo significa que tu perfil se ve más joven que el de una persona mayor — lo esperable y saludable.";
  }
  if (pct > 70) {
    return "Un valor alto significa que tu perfil se parece al de una persona de 70 años o más.";
  }
  return "Un valor intermedio: tu perfil está entre ambos extremos.";
}

function ResultSummary({ result }: { result: PredictResult }) {
  const similitud = Math.round(
    Math.max(0, Math.min(100, getProbabilityPercent(result.probabilidad)))
  );

  return (
    <section className="grid gap-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <p className="text-sm font-medium uppercase tracking-wide text-emerald-700">
          Tu resultado
        </p>
        <h2 className="mt-2 text-2xl font-semibold text-slate-950">
          Tu edad biológica
        </h2>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm text-slate-500">Tu edad real</p>
          <p className="mt-2 text-2xl font-semibold text-slate-950">
            {formatYears(result.edad_cronologica)}
          </p>
        </div>
        <div className="rounded-md border border-emerald-200 bg-emerald-50 p-4">
          <p className="text-sm text-emerald-700">Tu edad biológica</p>
          <p className="mt-2 text-2xl font-semibold text-emerald-800">
            {formatYears(result.edad_biologica)}
          </p>
        </div>
        <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm text-slate-500">Diferencia de edad</p>
          <p className="mt-2 text-2xl font-semibold text-slate-950">
            {formatGap(result.gap)}
          </p>
        </div>
      </div>

      <div className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-900">
        {getGapSentence(result.gap)}
      </div>

      {/* Aclara qué significa el % de "longevidad" para que no se malinterprete */}
      <div className="grid gap-2 rounded-md border border-slate-200 p-4">
        <div className="flex items-end justify-between gap-4">
          <p className="text-sm font-medium text-slate-700">
            Parecido con un perfil de 70+ años
          </p>
          <p className="text-3xl font-semibold text-slate-950">{similitud}%</p>
        </div>
        <div className="h-3 overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-emerald-500"
            style={{ width: `${similitud}%` }}
          />
        </div>
        <p className="text-sm leading-6 text-slate-600">
          Mide cuánto tus biomarcadores se parecen a los de una persona de 70 años
          o más. <strong>No</strong> es tu probabilidad de vivir mucho.{" "}
          {getSimilitudTexto(similitud)}
        </p>
      </div>
    </section>
  );
}

function MortalityCard({ result }: { result: MortalityResult }) {
  const pct = Math.round(Math.max(0, Math.min(100, result.riesgo_pct)));
  // Tono medido: la mortalidad es sensible, evitamos rojo alarmista para riesgos bajos.
  const tone =
    pct < 10
      ? { bar: "bg-emerald-500", chip: "bg-emerald-100 text-emerald-800", label: "bajo" }
      : pct < 30
        ? { bar: "bg-amber-500", chip: "bg-amber-100 text-amber-900", label: "moderado" }
        : { bar: "bg-rose-500", chip: "bg-rose-100 text-rose-800", label: "alto" };

  return (
    <section className="grid gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-semibold text-slate-950">
          Riesgo estimado a 10 años
        </h2>
        <span className={`rounded-md px-3 py-1 text-sm font-semibold ${tone.chip}`}>
          Riesgo {tone.label}
        </span>
      </div>

      <div className="flex items-end justify-between gap-4">
        <p className="text-sm text-slate-500">
          Probabilidad de fallecer en los próximos 10 años
        </p>
        <p className="text-4xl font-semibold text-slate-950">{pct}%</p>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${tone.bar}`} style={{ width: `${pct}%` }} />
      </div>

      <p className="text-sm leading-6 text-slate-600">
        Estimación <strong>poblacional</strong>: de cada 100 personas con un perfil de
        salud parecido al tuyo, alrededor de <strong>{pct}</strong> fallecerían en los
        próximos 10 años. <strong>No</strong> es una predicción individual ni un
        diagnóstico — es un promedio basado en datos de la encuesta NHANES.
      </p>
      <p className="text-xs leading-5 text-slate-400">
        Proyecto académico/educativo. La predicción de mortalidad es sensible y solo
        informativa; ante cualquier duda de salud, consulta a un profesional.
      </p>
    </section>
  );
}

function ShapBars({
  explainResult,
  labels
}: {
  explainResult: ExplainResult;
  labels: Record<string, string>;
}) {
  const maxMagnitude = Math.max(
    ...explainResult.contribuciones.map((contribution) =>
      Math.abs(contribution.shap)
    ),
    0
  );

  return (
    <section className="grid gap-5 rounded-md border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <h2 className="text-2xl font-semibold text-slate-950">
          ¿Qué influyó en tu resultado?
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Estos son los factores que más movieron <strong>tu</strong> predicción.
          En <span className="font-semibold text-emerald-700">verde</span>, los que
          te acercan a ser longevo/a; en{" "}
          <span className="font-semibold text-rose-700">rojo</span>, los que te
          alejan. Cuanto más larga la barra, más pesó ese factor.
        </p>
      </div>

      <div className="grid gap-4">
        {explainResult.contribuciones.map((contribution) => {
          const magnitude = Math.abs(contribution.shap);
          const width =
            maxMagnitude > 0 ? Math.max(6, (magnitude / maxMagnitude) * 100) : 0;
          const isPositive = contribution.empuja === "longevo";
          const nombre = labels[contribution.feature] ?? contribution.feature;

          return (
            <div className="grid gap-2" key={`${contribution.feature}-${contribution.shap}`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium text-slate-950">{nombre}</span>
                <span
                  className={
                    isPositive
                      ? "rounded-md bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-800"
                      : "rounded-md bg-rose-100 px-2 py-1 text-xs font-semibold text-rose-800"
                  }
                >
                  {isPositive ? "↑ Te acerca a longevo" : "↓ Te aleja de longevo"}
                </span>
              </div>
              <div className="h-3 overflow-hidden rounded-md bg-slate-100">
                <div
                  className={
                    isPositive
                      ? "h-full rounded-md bg-emerald-500"
                      : "h-full rounded-md bg-rose-500"
                  }
                  style={{ width: `${width}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <p className="text-xs leading-5 text-slate-400">
        Calculado con SHAP, una técnica que reparte el resultado entre los datos que
        ingresaste para ver cuánto aportó cada uno. No es un diagnóstico médico.
      </p>
    </section>
  );
}

// Bloque post-resultado: descargar el informe o recibirlo por correo (+ guardar).
function ReportActions({ payload }: { payload: PredictPayload }) {
  const [email, setEmail] = useState("");
  const [guardar, setGuardar] = useState(false);
  const [reportState, setReportState] = useState<ReportState>({
    status: "idle",
    message: null
  });

  async function requestReport(send: boolean) {
    if (send && !email.trim()) {
      setReportState({
        status: "error",
        message: "Ingresa tu correo para recibir el informe."
      });
      return;
    }

    setReportState({ status: "loading", message: null });

    try {
      const response = await fetchWithTimeout(REPORT_URL, {
        body: JSON.stringify({
          ...payload,
          email: send ? email.trim() : null,
          guardar: send ? guardar : false
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST"
      });
      const body = (await response.json().catch(() => null)) as ReportResult | null;

      if (!response.ok || !body) {
        throw new Error(
          body && "html" in body
            ? "No se pudo generar el informe"
            : `La API respondió ${response.status} al generar el informe`
        );
      }

      if (!send) {
        const esPdf = downloadReport(body);
        setReportState({
          status: "success",
          message: esPdf
            ? "Descargamos tu informe en PDF. Revisa tu carpeta de descargas."
            : "Descargamos tu informe. Ábrelo o imprímelo a PDF desde el navegador."
        });
        return;
      }

      const enviado =
        body.email_mode === "smtp"
          ? `Te enviamos el informe en PDF a ${email.trim()}.`
          : "Informe generado (modo demo: el envío real de correo está desactivado).";
      const guardadoMsg = body.guardado
        ? " Guardamos esta predicción en tu historial."
        : "";
      setReportState({ status: "success", message: enviado + guardadoMsg });
    } catch (error) {
      setReportState({
        status: "error",
        message:
          error instanceof Error
            ? getFetchErrorMessage(error, "No se pudo generar el informe")
            : "No se pudo generar el informe"
      });
    }
  }

  const loading = reportState.status === "loading";

  return (
    <section className="grid gap-4 rounded-md border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <h2 className="text-xl font-semibold text-slate-950">Llévate tu informe</h2>
        <p className="mt-1 text-sm text-slate-600">
          Descárgalo en <strong>PDF</strong> al instante o recíbelo por correo. Si lo
          deseas, guardamos esta predicción en tu historial (asociada a tu correo).
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
        <label className="grid gap-1" htmlFor="report-email">
          <span className="text-sm font-medium text-slate-950">Tu correo (opcional)</span>
          <input
            className="min-h-11 w-full rounded-md border border-slate-300 px-3 text-sm outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
            id="report-email"
            onChange={(event) => setEmail(event.target.value)}
            placeholder="tucorreo@ejemplo.com"
            type="email"
            value={email}
          />
        </label>
      </div>

      <label className="flex items-center gap-2 text-sm text-slate-700" htmlFor="report-guardar">
        <input
          checked={guardar}
          className="h-4 w-4 rounded border-slate-300 text-emerald-700 focus:ring-emerald-200"
          id="report-guardar"
          onChange={(event) => setGuardar(event.target.checked)}
          type="checkbox"
        />
        Guardar esta predicción en mi historial (podré consultarla con mi correo).
      </label>

      <div className="flex flex-wrap gap-3">
        <button
          className="min-h-11 rounded-md border border-emerald-700 px-5 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={loading}
          onClick={() => requestReport(false)}
          type="button"
        >
          {loading ? "Generando..." : "Descargar informe"}
        </button>
        <button
          className="min-h-11 rounded-md bg-emerald-700 px-5 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          disabled={loading}
          onClick={() => requestReport(true)}
          type="button"
        >
          {loading ? "Enviando..." : "Enviarme el informe"}
        </button>
      </div>

      {reportState.status === "success" && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-800">
          {reportState.message}
        </div>
      )}

      {reportState.status === "error" && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-800">
          {reportState.message}
        </div>
      )}
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
            step="any"
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

function FieldGroups({
  fields,
  fieldErrors
}: {
  fields: SchemaField[];
  fieldErrors: Record<string, string>;
}) {
  const groups = groupFields(fields);

  return (
    <>
      {Object.entries(groups).map(([groupName, groupFieldList]) => (
        <section className="grid gap-4" key={groupName}>
          <h3 className="text-base font-semibold text-slate-800">{groupName}</h3>
          <div className="grid gap-4 md:grid-cols-2">
            {groupFieldList.map((field) => (
              <FieldControl
                error={fieldErrors[field.code]}
                field={field}
                key={field.code}
              />
            ))}
          </div>
        </section>
      ))}
    </>
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
  const [mortalityResult, setMortalityResult] =
    useState<MortalityResult | null>(null);
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

  const tiers = useMemo(() => {
    if (schemaState.status !== "loaded") {
      return { essential: [], advanced: [] };
    }

    return partitionByTier(schemaState.data.features);
  }, [schemaState]);

  const edadCronologica = useMemo(() => {
    if (schemaState.status !== "loaded") {
      return undefined;
    }

    return normalizeExtraInputs(schemaState.data.extra_inputs).find(
      (field) => field.code === "edad_cronologica"
    );
  }, [schemaState]);

  // Mapa codigo NHANES -> etiqueta legible, para mostrar nombres humanos en el
  // panel SHAP (la API solo devuelve el codigo).
  const featureLabels = useMemo(() => {
    if (schemaState.status !== "loaded") {
      return {} as Record<string, string>;
    }
    const map: Record<string, string> = {};
    for (const field of schemaState.data.features) {
      map[field.code] = field.label;
    }
    return map;
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
    setMortalityResult(null);
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

      // Riesgo de mortalidad a 10 años: modelo aparte. Necesita la edad como
      // feature (RIDAGEYR = edad_cronologica). Best-effort: si no hay edad o
      // falla, simplemente no se muestra esa tarjeta.
      if (payload.edad_cronologica != null) {
        try {
          const mortResp = await fetchWithTimeout(MORTALITY_URL, {
            body: JSON.stringify({
              features: { ...payload.features, RIDAGEYR: payload.edad_cronologica }
            }),
            headers: { "Content-Type": "application/json" },
            method: "POST"
          });
          if (mortResp.ok) {
            setMortalityResult((await mortResp.json()) as MortalityResult);
          }
        } catch {
          // silencioso: la mortalidad es complementaria
        }
      }

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
      <section className="grid gap-6 rounded-md border border-slate-200 bg-slate-50 p-6">
        <div>
          <h2 className="text-xl font-semibold text-slate-950">Datos esenciales</h2>
          <p className="mt-1 text-sm text-slate-600">
            Solo lo fácil de saber. El IMC se calcula automáticamente desde tu peso y
            estatura.
          </p>
        </div>

        {edadCronologica && (
          <div className="grid gap-4 md:grid-cols-2">
            <FieldControl
              error={fieldErrors[edadCronologica.code]}
              field={edadCronologica}
            />
          </div>
        )}

        <FieldGroups fields={tiers.essential} fieldErrors={fieldErrors} />
      </section>

      {tiers.advanced.length > 0 && (
        <details className="rounded-md border border-slate-200 bg-white p-6">
          <summary className="cursor-pointer text-base font-semibold text-slate-800">
            Datos avanzados (opcional)
          </summary>
          <p className="mt-2 text-sm text-slate-600">
            Si los tienes a mano, afinan el resultado. Si no, el modelo los estima por
            ti.
          </p>
          <div className="mt-6 grid gap-6">
            <FieldGroups fields={tiers.advanced} fieldErrors={fieldErrors} />
          </div>
        </details>
      )}

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

          {mortalityResult && <MortalityCard result={mortalityResult} />}

          {explainState.status === "loading" && (
            <div className="rounded-md border border-slate-200 bg-white p-5 text-sm text-slate-700">
              Analizando qué influyó en tu resultado...
            </div>
          )}

          {explainState.status === "error" && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-5 text-sm font-medium text-amber-900">
              No se pudo cargar el detalle de tu resultado: {explainState.message}
            </div>
          )}

          {explainState.status === "success" && explainResult && (
            <ShapBars explainResult={explainResult} labels={featureLabels} />
          )}

          {lastPayload && <ReportActions payload={lastPayload} />}

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
