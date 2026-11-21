/**
 * MANUAL — gerar_timeline_historia_espaco.mjs
 * ============================================
 * O que faz
 * ---------
 * Lê os tempos oficiais (tempos-historia.json, medido por ffprobe no MP3
 * completo) e a sincronização labial RMS (sincronizacao-labial-historinha-
 * completa.json) entregues pelo Especialista-Áudio, e escreve em
 * src/projeto-historinha-espaco/:
 *   - timelineHistoriaEspaco.generated.ts (fronteiras em frames, 30 fps)
 *   - dadosBocaHistoriaEspaco.generated.ts (abertura da boca por frame)
 *
 * Por que existe
 * --------------
 * Os números nunca são digitados à mão. O áudio da historinha "Luninha e
 * Fridóca no Espaço Sideral" foi recontado em 10 blocos C0..C9 (106,82 s),
 * enquanto o código visual usa ids cena-00..cena-09; este gerador faz a ponte.
 *
 * Como rodar
 * ----------
 *   node tools/gerar_timeline_historia_espaco.mjs
 *
 * Regra de frame
 * --------------
 * Fronteira = inicioFrames/fimFrames do JSON oficial; duração = diferença.
 * NÃO somar gaps aqui — eles já estão dentro do MP3 completo.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const projeto = path.join(raiz, "src", "projeto-historinha-espaco");
const pastaAudio = path.join(raiz, "public", "historinha-espaco", "audio");

// 1. ids visuais (código) -> ids de áudio (entregues), mesma ordem do filme
const pares = Array.from({ length: 10 }, (_, i) => ({
  idVisual: `cena-0${i}`,
  idAudio: `C${i}`,
}));

// 2. tempos oficiais medidos no MP3 completo
const tempos = JSON.parse(
  fs.readFileSync(path.join(pastaAudio, "tempos-historia.json"), "utf8")
);
const porAudio = new Map(tempos.fronteirasDeCena.map((f) => [f.id, f]));

const cena = pares.map(({ idVisual, idAudio }) => {
  const f = porAudio.get(idAudio);
  if (!f) throw new Error(`Fronteira ausente para ${idAudio} em tempos-historia.json`);
  return {
    id: idVisual,
    inicioSegundos: f.inicioSegundos,
    duracaoSegundos: f.duracaoSegundos,
    inicioFrame: f.inicioFrames,
    duracaoFrames: f.fimFrames - f.inicioFrames,
  };
});

const totalFrames = tempos.totalFrames30fps;

// 3. timeline gerada
const tsTimeline = `/**
 * GENERATED — timelineHistoriaEspaco.generated.ts
 * Gerado por tools/gerar_timeline_historia_espaco.mjs. NÃO EDITE À MÃO.
 * Fonte: tempos-historia.json (ffprobe no MP3 completo, 106,82 s).
 * Total: ${tempos.duracaoMedidaSegundos} s / ${totalFrames} frames @ 30 fps.
 */
import type { TimelineHistoria } from "./timelineHistoriaEspaco";

export const TIMELINE_HISTORIA: TimelineHistoria = ${JSON.stringify(
  { fps: 30, totalFrames, totalSegundos: tempos.duracaoMedidaSegundos, cenas: cena },
  null,
  2
)};
`;

// 4. boca: RMS global por frame, fatiado pelas fronteiras de cena
const labial = JSON.parse(
  fs.readFileSync(
    path.join(pastaAudio, "sincronizacao-labial-historinha-completa.json"),
    "utf8"
  )
);
const valores = labial.valores;
const boca = {};
for (const c of cena) {
  boca[c.id] = valores
    .slice(c.inicioFrame, c.inicioFrame + c.duracaoFrames)
    .map((v) => Number(Number(v).toFixed(4)));
}

const tsBoca = `/**
 * GENERATED — dadosBocaHistoriaEspaco.generated.ts
 * Gerado por tools/gerar_timeline_historia_espaco.mjs. NÃO EDITE À MÃO.
 * Abertura da boca (0..1) por frame, pela energia RMS da narração real.
 * Fonte: sincronizacao-labial-historinha-completa.json (${valores.length} frames).
 */
export const BOCA_HISTORIA: Record<string, number[]> = ${JSON.stringify(boca, null, 1)};
`;

fs.writeFileSync(path.join(projeto, "timelineHistoriaEspaco.generated.ts"), tsTimeline);
fs.writeFileSync(path.join(projeto, "dadosBocaHistoriaEspaco.generated.ts"), tsBoca);
console.log(
  `Timeline escrita: ${tempos.duracaoMedidaSegundos}s / ${totalFrames} frames; boca ${valores.length} frames`
);
for (const c of cena) {
  console.log(
    `  ${c.id} <- ${pares.find((p) => p.idVisual === c.id).idAudio}  ${c.duracaoSegundos}s  inicio ${c.inicioFrame}  dur ${c.duracaoFrames}  boca ${boca[c.id].length}`
  );
}
