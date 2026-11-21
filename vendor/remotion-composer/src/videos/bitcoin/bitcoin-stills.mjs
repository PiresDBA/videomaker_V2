// usage: node src/videos/bitcoin/bitcoin-stills.mjs <outPrefix> <frame,frame,...> [scale]
// Adapted from the cartoon-3d-short skill's bridge-stills.mjs for the BitcoinShort composition.
// Remotion bundles copy public/ into the temp folder; keep that on the D: drive via REMOTION_TMP.
import fs from "node:fs";
if (process.env.REMOTION_TMP) {
  fs.mkdirSync(process.env.REMOTION_TMP, { recursive: true });
  process.env.TEMP = process.env.TMP = process.env.REMOTION_TMP;
}
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import path from "node:path";

const [prefix, frames, scale = "0.5"] = process.argv.slice(2);
const browserExecutable = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const chromiumOptions = { gl: "angle" };
const entry = process.env.BITCOIN_ENTRY || "src/index.tsx";
const serveUrl = await bundle({ entryPoint: path.resolve(entry), publicDir: path.resolve("public") });
const composition = await selectComposition({ serveUrl, id: "BitcoinShort", browserExecutable, chromiumOptions });
const onBrowserLog = (l) => {
  if (l.type === "error" || l.type === "warning") console.log(`[${l.type}]`, l.text.slice(0, 300));
};
for (const f of frames.split(",").map(Number)) {
  const t0 = Date.now();
  await renderStill({
    composition, serveUrl, frame: f, output: `${prefix}${f}.jpg`, imageFormat: "jpeg", jpegQuality: 88,
    scale: Number(scale), browserExecutable, chromiumOptions, timeoutInMilliseconds: 180000, onBrowserLog,
  });
  console.log("still", f, ((Date.now() - t0) / 1000).toFixed(1) + "s");
}
