import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Predictor de Longevidad",
  description: "Frontend inicial conectado a la API"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
