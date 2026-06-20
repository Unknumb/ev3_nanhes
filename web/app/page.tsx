import { SchemaForm } from "@/components/SchemaForm";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-950">
      <section className="mx-auto grid w-full max-w-5xl gap-8">
        <p className="mb-3 text-sm font-medium uppercase tracking-wide text-emerald-700">
          NHANES Longevity
        </p>
        <div>
          <h1 className="text-4xl font-semibold leading-tight sm:text-5xl">
            Predictor de Longevidad
          </h1>
          <p className="mt-4 text-lg leading-8 text-slate-700">
            Frontend inicial conectado a la API
          </p>
        </div>
        <SchemaForm />
      </section>
    </main>
  );
}
