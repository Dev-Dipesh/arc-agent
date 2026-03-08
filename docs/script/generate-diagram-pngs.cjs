#!/usr/bin/env node
/**
 * generate-diagram-pngs.cjs
 * -------------------------
 * Converts all PlantUML files from:
 *   ./puml/*.puml
 * to PNG files in:
 *   ./diagrams/*.png
 * using Kroki (https://kroki.io).
 *
 * Usage:
 *   node docs/script/generate-diagram-pngs.cjs
 *   node docs/script/generate-diagram-pngs.cjs <file.puml>
 *   node docs/script/generate-diagram-pngs.cjs puml/<file.puml>
 */

const fs = require("node:fs");
const path = require("node:path");
const https = require("node:https");

const BASE_DIR = __dirname;
const PUML_DIR = path.join(BASE_DIR, "puml");
const PNG_DIR = path.join(BASE_DIR, "diagrams");

function krokiPng(pumlText) {
  return new Promise((resolve, reject) => {
    const body = Buffer.from(pumlText, "utf8");
    const req = https.request(
      {
        hostname: "kroki.io",
        path: "/plantuml/png",
        method: "POST",
        headers: {
          "Content-Type": "text/plain; charset=utf-8",
          "Content-Length": body.length,
          Accept: "image/png",
        },
      },
      (res) => {
        const chunks = [];
        res.on("data", (chunk) => chunks.push(chunk));
        res.on("end", () => {
          const data = Buffer.concat(chunks);
          if (res.statusCode === 200) {
            resolve(data);
            return;
          }
          reject(
            new Error(
              `Kroki HTTP ${res.statusCode}: ${data.toString("utf8").slice(0, 300)}`,
            ),
          );
        });
      },
    );

    req.on("error", reject);
    req.write(body);
    req.end();
  });
}

async function main() {
  if (!fs.existsSync(PUML_DIR)) {
    console.error(`PlantUML directory not found: ${PUML_DIR}`);
    process.exit(1);
  }

  fs.mkdirSync(PNG_DIR, { recursive: true });

  const cliArg = process.argv[2]?.trim();
  let files;
  if (cliArg) {
    const candidate = path.basename(cliArg);
    if (!candidate.endsWith(".puml")) {
      console.error(`Expected a .puml file, got: ${cliArg}`);
      process.exit(1);
    }
    const inputPath = path.join(PUML_DIR, candidate);
    if (!fs.existsSync(inputPath)) {
      console.error(`File not found in ${PUML_DIR}: ${candidate}`);
      process.exit(1);
    }
    files = [candidate];
  } else {
    files = fs
      .readdirSync(PUML_DIR)
      .filter((file) => file.endsWith(".puml"))
      .sort((a, b) => a.localeCompare(b));
  }

  if (files.length === 0) {
    console.log("No .puml files found.");
    return;
  }

  let ok = 0;
  let failed = 0;

  for (const file of files) {
    const inputPath = path.join(PUML_DIR, file);
    const outName = `${path.basename(file, ".puml")}.png`;
    const outputPath = path.join(PNG_DIR, outName);
    const pumlText = fs.readFileSync(inputPath, "utf8");

    process.stdout.write(`Rendering ${file} -> ${outName} ... `);
    try {
      const pngBuffer = await krokiPng(pumlText);
      fs.writeFileSync(outputPath, pngBuffer);
      ok += 1;
      console.log("ok");
    } catch (err) {
      failed += 1;
      console.log("failed");
      const message = err instanceof Error ? err.message : String(err);
      console.error(`  ${message}`);
    }
  }

  console.log(`\nDone. Success: ${ok}, Failed: ${failed}`);
  if (failed > 0) {
    process.exitCode = 1;
  }
}

void main();
