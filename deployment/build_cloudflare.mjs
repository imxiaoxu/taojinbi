import { cpSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const PACKAGE_ROOT = resolve(HERE, "..");
const SOURCE = join(PACKAGE_ROOT, "dashboard");
const OUTPUT = join(HERE, "cloudflare_dist");
const API_BASE_URL = (process.env.RENDER_API_URL || "https://REPLACE-WITH-YOUR-SERVICE.onrender.com").replace(/\/$/, "");

rmSync(OUTPUT, { recursive: true, force: true });
mkdirSync(OUTPUT, { recursive: true });

for (const file of ["index.html", "dashboard_data.js", "agent_test_data.js"]) {
  cpSync(join(SOURCE, file), join(OUTPUT, file));
}

const indexPath = join(OUTPUT, "index.html");
const indexHtml = readFileSync(indexPath, "utf8").replaceAll("../synthetic_data/", "synthetic_data/");
writeFileSync(indexPath, indexHtml, "utf8");
writeFileSync(join(OUTPUT, "runtime-config.js"), `window.APP_CONFIG = ${JSON.stringify({ API_BASE_URL }, null, 2)};\n`, "utf8");
writeFileSync(join(OUTPUT, "_headers"), `/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: no-referrer\n  X-Frame-Options: DENY\n  Permissions-Policy: camera=(), microphone=(), geolocation=()\n`, "utf8");

const replaySource = join(PACKAGE_ROOT, "synthetic_data", "agent_full_replay", "full_agent_replay_results.csv");
if (existsSync(replaySource)) {
  const replayTarget = join(OUTPUT, "synthetic_data", "agent_full_replay");
  mkdirSync(replayTarget, { recursive: true });
  cpSync(replaySource, join(replayTarget, "full_agent_replay_results.csv"));
}

console.log(`Cloudflare bundle ready: ${OUTPUT}`);
console.log(`Render API: ${API_BASE_URL}`);
