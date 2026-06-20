import { readFileSync } from "fs";
import { resolve } from "path";
import type { NextConfig } from "next";

function loadRootEnv(): Record<string, string> {
  const envPath = resolve(__dirname, "../../.env");
  try {
    const content = readFileSync(envPath, "utf-8");
    const env: Record<string, string> = {};
    for (const line of content.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;
      const [key, ...rest] = trimmed.split("=");
      const k = key.trim();
      const v = rest.join("=").trim().replace(/^['"]|['"]$/g, "");
      env[k] = v;
    }
    return env;
  } catch {
    return {};
  }
}

const rootEnv = loadRootEnv();

// Inject root .env values into process.env so Next.js's NEXT_PUBLIC_* auto-inlining
// picks them up even when the shell environment has those variables set to empty strings.
for (const [k, v] of Object.entries(rootEnv)) {
  if (v && !process.env[k]) {
    process.env[k] = v;
  }
}

function envValue(key: string, fallback = ""): string {
  return process.env[key] || rootEnv[key] || fallback;
}

const nextConfig: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: ["127.0.0.1"],
  env: {
    NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: envValue("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY"),
    NEXT_PUBLIC_API_URL: envValue("NEXT_PUBLIC_API_URL"),
    NEXT_PUBLIC_WORKER_URL: envValue("NEXT_PUBLIC_WORKER_URL"),
    NEXT_PUBLIC_SIGNALLOOP_ENV: envValue("SIGNALLOOP_ENV", "local"),
  },
};

export default nextConfig;
