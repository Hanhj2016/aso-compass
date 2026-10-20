import { readdir, readFile, stat } from "node:fs/promises";
import { join } from "node:path";

const root = new URL("../dist/", import.meta.url);
const forbidden = [
  ["backend environment name", /OPENAI_API_KEY|DATABASE_URL|SUPABASE_SECRET_KEY|SUPABASE_SERVICE_ROLE_KEY/],
  ["PostgreSQL connection URL", /postgres(?:ql)?(?:\+psycopg)?:\/\//i],
  ["OpenAI-style secret", /\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b/],
  ["JWT-like service credential", /\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b/],
];

async function files(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(entries.map(async entry => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? files(path) : [path];
  }));
  return nested.flat();
}

const rootPath = root.pathname;
if (!(await stat(rootPath)).isDirectory()) throw new Error("dist/ is missing; run npm run build first");

const findings = [];
for (const path of await files(rootPath)) {
  const content = await readFile(path, "utf8").catch(() => "");
  for (const [label, pattern] of forbidden) {
    if (pattern.test(content)) findings.push(`${path.slice(rootPath.length)}: ${label}`);
  }
}

if (findings.length) {
  console.error("Potential backend secret material found in the browser bundle:");
  for (const finding of findings) console.error(`- ${finding}`);
  process.exitCode = 1;
} else {
  console.log("Browser bundle secret-marker audit passed.");
}
