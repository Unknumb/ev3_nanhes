import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Genera .next/standalone/server.js para una imagen Docker mínima.
  output: "standalone",
};

export default nextConfig;
