import { readdir, readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));

const IGNORED_DIRS = new Set([
  "node_modules",
  ".next",
  "out",
  "build",
  "dist",
  ".venv",
  "__pycache__",
  ".pytest_cache",
  ".ruff_cache",
  "data",
  "test-results",
  ".git",
]);

const REPO_PATH_PATTERN =
  /`((?:docs|apps|db|prompts|skills|scripts|\.agents)\/[A-Za-z0-9_.\-\/]+\.[A-Za-z0-9]+)`/g;

async function walk(dir, relBase = "") {
  const entries = await readdir(dir, { withFileTypes: true });
  const results = [];
  for (const entry of entries) {
    if (IGNORED_DIRS.has(entry.name)) continue;
    const relPath = relBase ? `${relBase}/${entry.name}` : entry.name;
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...(await walk(fullPath, relPath)));
    } else {
      results.push(relPath);
    }
  }
  return results;
}

function getAnchors(text) {
  const cleaned = text.replace(/^```[^\n]*\n[\s\S]*?^```/gm, "");
  const ids = new Set(
    [...cleaned.matchAll(/\bid=["']([^"']+)["']/g)].map((m) => m[1])
  );
  const duplicates = new Map();
  for (const match of cleaned.matchAll(/^#{1,6}\s+(.+)$/gm)) {
    const base = match[1]
      .trim()
      .toLowerCase()
      .replace(/<[^>]+>/g, "")
      .replace(/[^\p{L}\p{N}_\-\s]/gu, "")
      .replace(/\s+/g, "-");
    const count = duplicates.get(base) ?? 0;
    duplicates.set(base, count + 1);
    ids.add(count ? `${base}-${count}` : base);
  }
  return ids;
}

const files = await walk(root);
const anchors = new Map();
let checkedJson = 0;
let checkedLinks = 0;
let checkedRepoPaths = 0;
const warnings = [];

for (const file of files) {
  const fullPath = path.join(root, file);

  if (/\.json$/i.test(file)) {
    const raw = await readFile(fullPath, "utf8");
    JSON.parse(raw);
    checkedJson++;
  }

  const isProjectDoc =
    /\.md$/i.test(file) &&
    !file.startsWith(".agents/") &&
    !file.startsWith("apps/");
  if (!isProjectDoc) continue;

  const content = await readFile(fullPath, "utf8");
  const withoutCodeFences = content.replace(/^```[^\n]*\n[\s\S]*?^```/gm, "");

  // 1. Validate backticked repository file paths (e.g. `docs/01-produto.md`)
  for (const match of withoutCodeFences.matchAll(REPO_PATH_PATTERN)) {
    const candidate = match[1];
    if (candidate.includes("<") || candidate.includes("*")) continue;
    const resolved = path.resolve(root, candidate);
    const exists = await stat(resolved).catch(() => null);
    if (!exists) {
      warnings.push(`${file}: missing referenced repo path -> \`${candidate}\``);
    } else {
      checkedRepoPaths++;
    }
  }

  // 2. Validate standard Markdown links and HTML href/src
  const stripped = withoutCodeFences.replace(/`[^`\n]+`/g, "");
  const targets = [
    ...stripped.matchAll(/\]\(([^)]+)\)|\b(?:href|src)=["']([^"']+)["']/g),
  ].map((m) => m[1] ?? m[2]);

  for (let target of new Set(targets)) {
    if (!target) continue;
    target = target.trim().replace(/^<|>$/g, "");
    if (/^(?:[a-z]+:|\/\/)/i.test(target)) continue;

    const [relativePart, anchor] = target.split("#");
    const resolved = relativePart
      ? path.resolve(path.dirname(fullPath), decodeURIComponent(relativePart))
      : fullPath;

    const exists = await stat(resolved).catch(() => null);
    if (!exists) {
      warnings.push(`${file}: missing link target -> ${target}`);
      continue;
    }

    if (anchor && /\.md$/i.test(resolved) && exists.isFile()) {
      if (!anchors.has(resolved)) {
        anchors.set(resolved, getAnchors(await readFile(resolved, "utf8")));
      }
      if (!anchors.get(resolved).has(decodeURIComponent(anchor))) {
        warnings.push(`${file}: missing anchor -> ${target}`);
        continue;
      }
    }
    checkedLinks++;
  }
}

console.log(
  `Validated: ${checkedRepoPaths} backticked repo paths, ${checkedLinks} Markdown links/anchors, and ${checkedJson} JSON files.`
);
if (warnings.length > 0) {
  console.warn(`Found ${warnings.length} reference warning(s):`);
  for (const w of warnings) console.warn(`  - ${w}`);
} else {
  console.log("PASS documentation integrity check.");
}
