import { GlobalImportanceChart } from "@/components/GlobalImportanceChart";
import { ModelStats } from "@/components/ModelStats";
import { SchemaForm } from "@/components/SchemaForm";
import { SocialProof } from "@/components/SocialProof";

const TRUST_POINTS = [
  { title: "Gratis y en 2 minutos", body: "Solo unos datos fáciles de saber." },
  { title: "Privado por defecto", body: "No pedimos login; los datos son tuyos." },
  { title: "Basado en datos del CDC", body: "Modelo entrenado con encuestas NHANES." }
];

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-950">
      <div className="mx-auto grid w-full max-w-5xl gap-12">
        {/* Hero + propuesta de valor */}
        <section className="grid gap-6">
          <p className="text-sm font-medium uppercase tracking-wide text-emerald-700">
            NHANES Longevity
          </p>
          <div className="grid gap-4">
            <h1 className="text-4xl font-semibold leading-tight sm:text-5xl">
              Descubre tu <span className="text-emerald-700">edad biológica</span> en
              2 minutos
            </h1>
            <p className="max-w-2xl text-lg leading-8 text-slate-700">
              Tu cuerpo puede ser más joven o más viejo que tu edad real. Responde unos
              datos simples y una IA entrenada con miles de personas estima la edad que
              aparenta tu cuerpo y tu probabilidad de llegar a viejo/a, y te explica en
              palabras claras qué influyó.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            <a
              className="inline-flex min-h-11 items-center justify-center rounded-md bg-emerald-700 px-6 text-sm font-semibold text-white transition hover:bg-emerald-800"
              href="#formulario"
            >
              Calcular mi edad biológica
            </a>
            <SocialProof />
          </div>

          <ul className="grid gap-4 sm:grid-cols-3">
            {TRUST_POINTS.map((point) => (
              <li
                className="rounded-md border border-slate-200 bg-white p-4"
                key={point.title}
              >
                <p className="text-sm font-semibold text-slate-950">{point.title}</p>
                <p className="mt-1 text-sm text-slate-600">{point.body}</p>
              </li>
            ))}
          </ul>
        </section>

        {/* Gráficos introductorios del modelo */}
        <section className="grid gap-6">
          <div>
            <h2 className="text-2xl font-semibold text-slate-950">
              Qué tan bien funciona el modelo
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              Medido sobre datos que el modelo nunca vio durante el entrenamiento.
            </p>
          </div>
          <ModelStats />
          <GlobalImportanceChart />
        </section>

        {/* Formulario */}
        <section className="grid gap-6 scroll-mt-6" id="formulario">
          <div>
            <h2 className="text-2xl font-semibold text-slate-950">
              Calcula tu edad biológica
            </h2>
            <p className="mt-2 text-base leading-7 text-slate-700">
              Responde unas preguntas fáciles sobre tu salud y te decimos qué edad
              aparenta tu cuerpo y qué tan probable es que llegues a longevo/a (70+
              años). Toma unos 2 minutos y no necesitas saber nada de tecnología.
            </p>

            <ol className="mt-4 grid gap-3 sm:grid-cols-3">
              {[
                {
                  n: "1",
                  t: "Completa lo esencial",
                  d: "Datos que ya conoces: peso, estatura, presión, si fumas…"
                },
                {
                  n: "2",
                  t: "El laboratorio es opcional",
                  d: "¿No tienes análisis de sangre? Tranquilo, el modelo lo estima por ti."
                },
                {
                  n: "3",
                  t: "Mira tu resultado",
                  d: "Tu edad biológica, tu probabilidad y qué factores influyeron."
                }
              ].map((step) => (
                <li
                  className="rounded-xl border border-slate-200 bg-white p-4"
                  key={step.n}
                >
                  <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-emerald-100 text-sm font-bold text-emerald-800">
                    {step.n}
                  </span>
                  <p className="mt-2 text-sm font-semibold text-slate-950">{step.t}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-600">{step.d}</p>
                </li>
              ))}
            </ol>

            <p className="mt-3 text-sm text-slate-500">
              Al final puedes descargar tu informe o recibirlo por correo.
            </p>
          </div>
          <SchemaForm />
        </section>

        <p className="text-xs leading-5 text-slate-400">
          Proyecto académico/educativo. No es consejo médico ni diagnóstico. La “edad
          biológica” es una estimación poblacional a partir de biomarcadores NHANES
          (CDC), no una medición clínica.
        </p>
      </div>
    </main>
  );
}
