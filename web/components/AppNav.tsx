import Link from "next/link";

const navItems = [
  { href: "/", label: "Operativa" },
  { href: "/mis-predicciones", label: "Mis predicciones" },
  { href: "/metrics", label: "Técnica/Métricas" },
  { href: "/executive", label: "Ejecutiva" }
];

export function AppNav() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex w-full max-w-5xl flex-col gap-3 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
        <Link className="text-base font-semibold text-slate-950" href="/">
          Predictor de Longevidad
        </Link>
        <div className="flex flex-wrap gap-2">
          {navItems.map((item) => (
            <Link
              className="rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-emerald-600 hover:text-emerald-700"
              href={item.href}
              key={item.href}
            >
              {item.label}
            </Link>
          ))}
        </div>
      </nav>
    </header>
  );
}
