export default function ExecutivePage() {
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-950">
      <section className="mx-auto grid w-full max-w-5xl gap-6">
        <div>
          <p className="mb-3 text-sm font-medium uppercase tracking-wide text-emerald-700">
            NHANES Longevity
          </p>
          <h1 className="text-4xl font-semibold leading-tight sm:text-5xl">
            Vista ejecutiva
          </h1>
        </div>

        <div className="rounded-md border border-slate-200 bg-white p-6 text-slate-700">
          Vista ejecutiva pendiente de GET /aggregates
        </div>
      </section>
    </main>
  );
}
